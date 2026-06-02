"""
Lazada Open Platform connector
เอกสาร: https://open.lazada.com/apps/doc/doc

การเซ็น signature:
  1) เรียงพารามิเตอร์ทั้งหมด (ยกเว้น sign) ตาม key แบบ ascii
  2) concat = api_path + (key1+value1) + (key2+value2) + ...
  3) sign = HMAC-SHA256(app_secret, concat) -> hex แล้ว .upper()
"""
import time
import hmac
import hashlib
import requests
from typing import List
from .base import BaseConnector, Order, OrderItem, Product, AdRecord


class LazadaConnector(BaseConnector):
    platform = "lazada"

    def _sign(self, api_path: str, params: dict) -> str:
        ordered = "".join(f"{k}{params[k]}" for k in sorted(params))
        base = api_path + ordered
        return hmac.new(
            self.cfg["app_secret"].encode(),
            base.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

    def _call(self, api_path: str, extra: dict = None) -> dict:
        params = {
            "app_key": self.cfg["app_key"],
            "access_token": self.cfg["access_token"],
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
        }
        if extra:
            params.update({k: str(v) for k, v in extra.items()})
        params["sign"] = self._sign(api_path, params)
        r = requests.get(self.cfg["base_url"] + api_path, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- Orders ----
    def fetch_orders(self, start: str, end: str) -> List[Order]:
        orders: List[Order] = []
        resp = self._call("/orders/get", {
            "created_after": start, "created_before": end,
            "limit": 100, "offset": 0, "sort_direction": "DESC",
        })
        for o in resp.get("data", {}).get("orders", []):
            items_resp = self._call("/order/items/get",
                                    {"order_id": o["order_id"]})
            items = [OrderItem(
                sku=it.get("sku", ""),
                product_name=it.get("name", ""),
                qty=1,
                unit_price=float(it.get("item_price", 0)),
            ) for it in items_resp.get("data", [])]
            orders.append(Order(
                platform=self.platform,
                order_id=str(o.get("order_id", "")),
                created_at=o.get("created_at", "")[:10],
                status=o.get("statuses", ["unknown"])[0],
                items=items,
            ))
        return orders

    # ---- Products / stock ----
    def fetch_products(self) -> List[Product]:
        prods: List[Product] = []
        resp = self._call("/products/get", {"limit": 100, "offset": 0, "filter": "live"})
        for p in resp.get("data", {}).get("products", []):
            for sk in p.get("skus", [{}]):
                prods.append(Product(
                    platform=self.platform,
                    sku=sk.get("SellerSku", ""),
                    name=p.get("attributes", {}).get("name", ""),
                    stock=int(sk.get("quantity", 0)),
                    price=float(sk.get("price", 0)),
                ))
        return prods

    # ---- Ads (Sponsored Solutions / Sponsored Discovery) ----
    def fetch_ads(self, start: str, end: str) -> List[AdRecord]:
        return []
