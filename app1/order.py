from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .schemas import MenuItem, OrderItem, OrderState


@dataclass
class OrderManager:
    order: OrderState = field(default_factory=OrderState)

    def add(self, menu_item: MenuItem, quantity: int = 1) -> str:
        # existing?
        existing = next((x for x in self.order.items if x.urun.lower() == menu_item.urun.lower()), None)
        if existing:
            existing.quantity += quantity
            existing.total = existing.quantity * existing.Fiyat
        else:
            self.order.items.append(
                OrderItem(
                    urun=menu_item.urun,
                    quantity=quantity,
                    Fiyat=float(menu_item.Fiyat),
                    total=float(menu_item.Fiyat) * quantity,
                )
            )

        self.order.total = sum(x.total for x in self.order.items)
        return f"{quantity}x {menu_item.urun} siparişinize eklendi. Toplam: {self.order.total:.2f} TL"

    def remove(self, item_name: str, quantity: Optional[int] = None) -> str:
        idx = next((i for i, x in enumerate(self.order.items) if x.urun.lower() == item_name.lower()), None)
        if idx is None:
            return f"{item_name} mevcut siparişinizde bulunmuyor."

        item = self.order.items[idx]
        if quantity is None or quantity >= item.quantity:
            self.order.items.pop(idx)
            self.order.total = sum(x.total for x in self.order.items)
            return f"{item.urun} siparişinizden çıkarıldı."
        else:
            item.quantity -= quantity
            item.total = item.quantity * item.Fiyat
            self.order.total = sum(x.total for x in self.order.items)
            return f"{quantity}x {item.urun} siparişinizden çıkarıldı."

    def summary_text(self) -> str:
        if not self.order.items:
            return "Henüz sipariş verilmedi."

        lines = ["=== SİPARİŞ ÖZETİ ==="]
        for x in self.order.items:
            lines.append(f"• {x.urun} x {x.quantity} = {x.total:.2f} TL")
        lines.append("=" * 22)
        lines.append(f"TOPLAM TUTAR: {self.order.total:.2f} TL")
        lines.append("=" * 22)
        return "\n".join(lines)

    def final_order_text(self) -> str:
        # istersen daha “onay” formatı
        return self.summary_text()

    def save_to_file(self, path: str) -> None:
        content = self.final_order_text()
        with open(path, "w", encoding="utf-8") as f:
            f.write("=== Sipariş Detayları ===\n")
            f.write(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(content)
            f.write("\n\n=== Sipariş Sonu ===\n")