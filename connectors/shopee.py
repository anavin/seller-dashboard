"""
Shopee Open Platform API v2 connector
เอกสาร: https://open.shopee.com/documents

การเซ็น signature (Shop API):
  base_string = f"{partner_id}{api_path}{timestamp}{access_token}{shop_id}"
  sign = HMAC-SHA256(partner_key, base_string)  -> hex (lowercase)

ทุก request แนบ query: partner_id, timestamp, access_token, shop_id, sign
"""
import time
import hmac
import hashlib
import requests
from typing import List
from .base import BaseConnector, Order, OrderItem, Product, AdRecord


class ShopeeConnector(BaseConnector):
    platform = "shopee"

    def _sign(self, api_path: str, timestamp: int) -> str:
        base = f"{self.cfg['partner_id']}{api_path}{timestamp}{self.cfg['access_token']}{self.cfg['shop_id']}"
        return hmac.new(
            self.cfg["partner_key"].encode(),
            base.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _call(self, api_path: str, extra: dict = None, method: str = "GET") -> dict:
        ts = int(time.time())
        params = {
            "partner_id": self.cfg["partner_id"],
            "timestamp": ts,
            "access_token": self.cfg["access_token"],
            "shop_id": self.cfg["shop_id"],
            "sign": self._sign(api_path, ts),
        }
        if extra:
            params.update(extra)
        url = self.cfg["base_url"] + api_path
        if method == "GET":
            r = requests.get(url, params=params, timeout=30)
        else:
            r = requests.post(url, params=params, json=extra, timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- Orders ----
    def fetch_orders(self, start: str, end: str) -> List[Order]:
        # /api/v2/order/get_order_list -> ได้ order_sn list
        # /api/v2/order/get_order_detail -> ได้รายละเอียด item, ค่าธรรมเนียม
        # NOTE: โค้ดด้านล่างเป็นโครง พร้อมเติมเมื่อมี credential จริง
        orders: List[Order] = []
        resp = self._call("/api/v2/order/get_order_list", {
            "time_range_field": "create_time",
            "time_from": start, "time_to": end,
            "page_size": 100, "order_status": "READY_TO_SHIP",
        })
        for o in resp.get("response", {}).get("order_list", []):
            detail = self._call("/api/v2/order/get_order_detail",
                                {"order_sn_list": o["order_sn"]})
            d = detail.get("response", {}).get("order_list", [{}])[0]
            items = [OrderItem(
                sku=it.get("model_sku") or it.get("item_sku", ""),
                product_name=it.get("item_name", ""),
                qty=it.get("model_quantity_purchased", 1),
                unit_price=float(it.get("model_discounted_price", 0)),
            ) for it in d.get("item_list", [])]
            orders.append(Order(
                platform=self.platform,
                order_id=d.get("order_sn", ""),
                created_at=d.get("create_time", ""),
                status=d.get("order_status", "").lower(),
                items=items,
            ))
        return orders

    # ---- Products / stock ----
    def fetch_products(self) -> List[Product]:
        prods: List[Product] = []
        resp = self._call("/api/v2/product/get_item_list",
                          {"offset": 0, "page_size": 100, "item_status": "NORMAL"})
        for it in resp.get("response", {}).get("item", []):
            prods.append(Product(
                platform=self.platform,
                sku=str(it.get("item_id", "")),
                name=it.get("item_name", ""),
                stock=it.get("stock", 0),
                price=float(it.get("price", 0)),
            ))
        return prods

    # ---- Ads ----
    def fetch_ads(self, start: str, end: str) -> List[AdRecord]:
        # Shopee Ads อยู่ภายใต้ /api/v2/ads (ต้องขอ scope เพิ่ม)
        return []
