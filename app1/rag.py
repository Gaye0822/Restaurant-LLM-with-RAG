from __future__ import annotations

import base64
import io
import json
import os
from typing import Any, Dict, Optional
import re
import pandas as pd
from gtts import gTTS
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .schemas import MenuItem
from .order import OrderManager
from .intent import IntentRouter


PROMPT_TEMPLATE = """You are a helpful and friendly Turkish restaurant waiter. Use the following information to help the customer.

Menu Context:
{context}

Current Order Status:
{current_order}

Chat History:
{chat_history}

Customer: {question}
{human_input}

Instructions:
YOUR NAME IS "MUTLU GARSON"
Avoid providing incomplete information when answering. Never skip any items from the menu when the customer asks for it.
If the customer asks for the menu, provide the full list of items (including all dish names and descriptions). Only include prices if the customer specifically requests them.

1. Help customers understand the menu and answer their questions naturally.
2. Provide the full menu when explicitly asked. Do not include prices unless specifically requested.
3. List menu items within a given price range when the customer provides one.
4. If asked about an unavailable item, inform the customer politely that it is not on the menu and suggest the closest available alternative.
5. Answer ingredient-related and pricing questions accurately when prompted.
6. Track and confirm the current order to avoid mistakes.
7. Handle special requests or modifications professionally, respecting the menu limitations.
8. Maintain a friendly and professional tone throughout the interaction.
9. Always respond in Turkish.

DIET / ALLERGEN RULES (IMPORTANT):
- If the user asks for vegan/vegetarian/gluten-free/lactose-free or similar diet/allergen constraints, you MUST base your answer ONLY on the Menu Context provided.
- In these cases, DO NOT assume anything not written in the Menu Context.
- Always list at least 3 options if available; if fewer than 3 exist, say exactly how many you found.
- For each suggested item, include a short evidence snippet from its ingredients, like:
  "Ürün — Neden uygun? (kanıt: <ingredients'den kısa ifade>)"
- Never say "we don't have X" if X exists in the Menu Context.

IMPORTANT FORMAT RULES:
1. If the customer's message contains ANY indication of ordering, adding, or removing items, you MUST respond in this exact JSON format:
{{"add_items": [{{"urun": "item_name", "quantity": number}}], "remove_items": [{{"urun": "item_name", "quantity": number}}], "response": "Your friendly Turkish response"}}

2. For regular questions about menu or general conversation, respond normally in Turkish without JSON format.

Assistant:
"""


class RestaurantRAG:
    def __init__(self, menu_csv_path: str):
        self.router = IntentRouter()
        self.menu_csv_path = menu_csv_path
        self.menu_items = self._load_menu_items(menu_csv_path)

        self.order_manager = OrderManager()
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True,input_key='question')

        self.vector_store = self._build_vector_store()
        self.qa_chain = self._build_chain()
        self.prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question", "chat_history", "current_order", "human_input"],
    )

    def _load_menu_items(self, csv_path: str):
        df = pd.read_csv(
            csv_path,
            sep=";",          # ÖNEMLİ
               # Header yok
              # Kolon isimleri
            engine="python"
        )

        items = []
        for _, r in df.iterrows():
            items.append(
                MenuItem(
                    urun=str(r["urun"]),
                    ingredients=str(r["ingredients"]),
                    category=str(r["category"]),
                    Fiyat=float(r["Fiyat"]),
                )
            )

        return items
    
    def is_diet_query(self, text: str) -> bool:
        DIET_KEYWORDS = [
            "vegan", "vejetaryen", "vegetarian", "glutensiz", "gluten-free",
            "laktozsuz", "dairy-free", "süt içermez", "yumurta içermez",
            "alerji", "alerjim", "içermez", "içermesin", "allergen"
        ]
        t = (text or "").lower()
        return any(k in t for k in DIET_KEYWORDS)
    
    def get_full_menu_context(self) -> str:
        lines = []
        for x in self.menu_items:
            lines.append(
                f"Ürün: {x.urun}\n"
                f"Kategori: {x.category}\n"
                f"İçindekiler: {x.ingredients}\n"
                f"Fiyat: {x.Fiyat}\n"
            )
        return "\n---\n".join(lines)

    def get_menu_text(self, category: Optional[str] = None) -> str:
        if category:
            items = [x for x in self.menu_items if x.category.lower() == category.lower()]
            if not items:
                return f"Bu kategoride ürün bulunamadı: {category}"
            out = [f"{category.upper()} MENÜSÜ:"]
            for x in items:
                out.append(f"• {x.urun} - İçindekiler: {x.ingredients}")
            return "\n".join(out)

        # full menu grouped
        categories: Dict[str, list[MenuItem]] = {}
        for x in self.menu_items:
            categories.setdefault(x.category or "Diğer", []).append(x)

        lines = ["TAM MENÜ:"]
        for cat, items in categories.items():
            lines.append(f"\n{cat.upper()}:")
            for x in items:
                lines.append(f"• {x.urun} - İçindekiler: {x.ingredients}")
        return "\n".join(lines)

    def _build_vector_store(self) -> FAISS:
        # Menü dokümanı: istersen satır satır doc yapabilirsin
        docs = []
        for x in self.menu_items:
            docs.append(f"Ürün: {x.urun}\nKategori: {x.category}\nİçindekiler: {x.ingredients}\nFiyat: {x.Fiyat}\n")

        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        return FAISS.from_texts(docs, embedding=embeddings)

    def _build_chain(self) -> ConversationalRetrievalChain:
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["context", "question", "chat_history", "current_order", "human_input"],
        )

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens=2000)

        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 30, "fetch_k": 40, "lambda_mult": 0.7},
            ),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": prompt},
            return_source_documents=False,
            chain_type="stuff",
            verbose=False,
        )

    def _try_json_parsing(self, text: str) -> Optional[dict]:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None

    def _apply_actions(self, actions: dict) -> None:
        # add
        for item in actions.get("add_items", []) or []:
            if not isinstance(item, dict):
                continue
            name = item.get("urun")
            qty = int(item.get("quantity", 1) or 1)
            if not name:
                continue
            menu_item = next((x for x in self.menu_items if x.urun.lower() == str(name).lower()), None)
            if menu_item:
                self.order_manager.add(menu_item, qty)

        # remove
        for item in actions.get("remove_items", []) or []:
            if not isinstance(item, dict):
                continue
            name = item.get("urun")
            qty = item.get("quantity", None)
            if not name:
                continue
            self.order_manager.remove(str(name), int(qty) if qty is not None else None)

    async def process_message(self, message: str) -> Dict[str, Any]:
        message = (message or "").strip()

        # 1) Intent routing (önce!)
        intent_res = self.router.classify(message)

        # 1.a) Menü isteği: deterministic cevap (LLM'e gitme)
        if intent_res.intent == "menu":
            answer = self.get_menu_text()

            # TTS
            tts = gTTS(text=answer, lang="tr")
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            audio_b64 = base64.b64encode(audio_io.read()).decode("utf-8")

            return {
                "text": answer,
                "audio": audio_b64,
                "order": self.order_manager.order.model_dump(),
            }

        # 2) Diyet/alerjen soruları: full menu context ile direkt LLM (retriever yok)
        if self.is_diet_query(message):
            full_context = self.get_full_menu_context()
            chat_history = self.memory.load_memory_variables({}).get("chat_history", [])

            prompt_text = self.prompt.format(
                context=full_context,
                question=message,
                chat_history=chat_history,
                current_order=self.order_manager.summary_text(),
                human_input="",
            )

            llm_resp = await self.llm.ainvoke(prompt_text)
            answer = llm_resp.content if hasattr(llm_resp, "content") else str(llm_resp)

            # memory'yi manuel güncelle
            self.memory.save_context({"question": message}, {"answer": answer})

            # Sipariş JSON aksiyonları gelirse uygula
            actions = self._try_json_parsing(answer)
            if actions:
                self._apply_actions(actions)
                answer = actions.get("response", answer)

            # TTS
            tts = gTTS(text=answer, lang="tr")
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            audio_b64 = base64.b64encode(audio_io.read()).decode("utf-8")

            return {
                "text": answer,
                "audio": audio_b64,
                "order": self.order_manager.order.model_dump(),
            }

        # 3) Normal durum: RAG retrieval chain
        inputs = {
            "question": message,
            "current_order": self.order_manager.summary_text(),
            "human_input": "",
        }

        response = await self.qa_chain.ainvoke(inputs)
        answer = response["answer"]

        # Sipariş JSON aksiyonları gelirse uygula
        actions = self._try_json_parsing(answer)
        if actions:
            self._apply_actions(actions)
            answer = actions.get("response", answer)

        # TTS
        tts = gTTS(text=answer, lang="tr")
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        audio_b64 = base64.b64encode(audio_io.read()).decode("utf-8")

        return {
            "text": answer,
            "audio": audio_b64,
            "order": self.order_manager.order.model_dump(),
        }