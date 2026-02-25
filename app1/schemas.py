from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    urun: str
    ingredients: str = ""
    category: str = ""
    Fiyat: float = 0.0


class OrderItem(BaseModel):
    urun: str
    quantity: int = Field(default=1, ge=1)
    Fiyat: float = 0.0
    total: float = 0.0


class OrderState(BaseModel):
    items: List[OrderItem] = Field(default_factory=list)
    total: float = 0.0


class WSIncoming(BaseModel):
    type: str  # "text" | "voice" | "close" | "order_confirm"
    text: Optional[str] = ""
    confirm: Optional[bool] = None