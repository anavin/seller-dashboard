"""
โครงสร้างกลางของทุก connector
แต่ละแพลตฟอร์มจะ return ข้อมูลในรูปแบบ "กลาง" (normalized) เหมือนกัน
เพื่อให้ ETL และ dashboard ใช้ต่อได้ทันที
"""
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class OrderItem:
    sku: str
    product_name: str
    qty: int
    unit_price: float       # ราคาขายต่อชิ้น
    unit_cost: float = 0.0   # ต้นทุนต่อชิ้น (เติมเองจากไฟล์ต้นทุน)
    category: str = ""       # หมวดหมู่สินค้า (มิติสำหรับ slice)


@dataclass
class Order:
    platform: str          # "tiktok" | "shopee" | "lazada"
    order_id: str
    created_at: str        # ISO date "YYYY-MM-DD"
    status: str            # paid / shipped / completed / cancelled / returned
    items: List[OrderItem] = field(default_factory=list)
    shipping_fee: float = 0.0
    platform_fee: float = 0.0   # ค่าธรรมเนียม + ค่าคอม platform
    hour: int = 12              # ชั่วโมงที่สั่งซื้อ 0-23 (มิติ heatmap)
    region: str = ""           # ภูมิภาค/จังหวัดผู้ซื้อ
    customer_type: str = "new"  # new | returning

    @property
    def gross(self) -> float:
        return sum(i.qty * i.unit_price for i in self.items)


@dataclass
class Product:
    platform: str
    sku: str
    name: str
    stock: int
    price: float
    cost: float = 0.0
    status: str = "active"
    category: str = ""


@dataclass
class AdRecord:
    platform: str
    date: str              # "YYYY-MM-DD"
    campaign: str
    spend: float
    impressions: int
    clicks: int
    orders: int
    revenue: float         # ยอดขายที่มาจากโฆษณา


class BaseConnector:
    """connector แต่ละแพลตฟอร์มสืบทอด class นี้แล้ว implement 3 เมธอด"""
    platform = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch_orders(self, start: str, end: str) -> List[Order]:
        raise NotImplementedError

    def fetch_products(self) -> List[Product]:
        raise NotImplementedError

    def fetch_ads(self, start: str, end: str) -> List[AdRecord]:
        raise NotImplementedError


def to_dict(obj):
    return asdict(obj)
