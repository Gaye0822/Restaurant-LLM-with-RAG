from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

Intent = Literal["menu", "faq", "order", "bye", "unknown"]


_ORDER_PATTERNS = [
    r"\bsipariş\b",
    r"\bsiparis\b",
    r"\bistiyorum\b",
    r"\bisterim\b",
    r"\bal(abilir)? miyim\b",
    r"\bekle\b",
    r"\bçıkar\b",
    r"\biptal\b",
    r"\b2 adet\b|\b3 adet\b|\b4 adet\b|\b5 adet\b",
]

_MENU_PATTERNS = [
    r"\bmenü\b",
    r"\bmenu\b",
    r"\bne var\b",
    r"\bneler var\b",
    r"\btüm menü\b",
    r"\bfiyat listesi\b",
]

_BYE_PATTERNS = [
    r"\bgörüşürüz\b",
    r"\bye?bye\b",
    r"\bçık\b",
    r"\bkapat\b",
    r"\bteşekkür(ler)?\b",
    r"\bsağ ol\b",
]


def _match_any(patterns: list[str], text: str) -> bool:
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            return True
    return False


@dataclass
class IntentResult:
    intent: Intent
    reason: str = ""
    wants_prices: bool = False


class IntentRouter:
    """
    Basit intent routing.
    İleride bunu LLM classifier'a yükseltebilirsin (aynı interface ile).
    """

    def classify(self, message: str) -> IntentResult:
        text = (message or "").strip()
        if not text:
            return IntentResult(intent="unknown", reason="empty")

        wants_prices = bool(re.search(r"\bfiyat\b|\bkaç tl\b|\bne kadar\b", text, flags=re.IGNORECASE))

        if _match_any(_BYE_PATTERNS, text):
            return IntentResult(intent="bye", reason="bye_pattern", wants_prices=wants_prices)

        # Menü isteme
        if _match_any(_MENU_PATTERNS, text):
            return IntentResult(intent="menu", reason="menu_pattern", wants_prices=wants_prices)

        # Sipariş niyeti
        if _match_any(_ORDER_PATTERNS, text):
            return IntentResult(intent="order", reason="order_pattern", wants_prices=wants_prices)

        # Default: soru/faq
        return IntentResult(intent="faq", reason="default_faq", wants_prices=wants_prices)