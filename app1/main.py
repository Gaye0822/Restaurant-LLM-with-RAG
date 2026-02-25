from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from openai import OpenAI

from .rag import RestaurantRAG


APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))

MENU_PATH = os.path.join(ROOT_DIR, "data1", "menu.csv")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs1")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

SIPARIS_PATH = os.path.join(OUTPUTS_DIR, "siparisler.txt")

app = FastAPI()

# static
STATIC_DIR = os.path.join(ROOT_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

restaurant = RestaurantRAG(MENU_PATH)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()
from pydantic import BaseModel

class ChatRequest(BaseModel):
    text: str

@app.post("/chat")
async def chat(req: ChatRequest):
    return await restaurant.process_message(req.text)

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="tr",
            )

        return {"text": transcript.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            text = data.get("text", "") or ""

            if msg_type == "close":
                # sipariş onayı iste
                if restaurant.order_manager.order.items:
                    final_order = restaurant.order_manager.final_order_text()
                    await websocket.send_json(
                        {
                            "type": "order_confirmation",
                            "text": "Siparişinizi onaylıyor musunuz?\n" + final_order,
                            "orderDetails": final_order,
                        }
                    )
                else:
                    await websocket.send_json(
                        {"type": "close", "text": "Bizi tercih ettiğiniz için teşekkürler! İyi günler!"}
                    )

            elif msg_type == "order_confirm":
                confirm = bool(data.get("confirm", False))
                if confirm:
                    restaurant.order_manager.save_to_file(SIPARIS_PATH)
                    await websocket.send_json(
                        {
                            "type": "order_saved",
                            "text": "Siparişiniz onaylandı ve kaydedildi.\nBizi tercih ettiğiniz için teşekkürler!",
                            "orderDetails": restaurant.order_manager.final_order_text(),
                        }
                    )
                else:
                    await websocket.send_json(
                        {"type": "order_cancelled", "text": "Sipariş iptal edildi.\nBizi tercih ettiğiniz için teşekkürler!"}
                    )

            elif msg_type in ("text", "voice"):
                resp = await restaurant.process_message(text)
                await websocket.send_json(resp)

            else:
                await websocket.send_json({"text": "Bilinmeyen mesaj tipi.", "audio": None})

    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.send_json({"text": "Bir hata oluştu. Sayfayı yenileyip tekrar deneyin.", "audio": None})
        except Exception:
            pass