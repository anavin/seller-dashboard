"""
TikTok Shop Partner API connector (เวอร์ชัน 202309+)
เอกสาร: https://partner.tiktokshop.com/docv2

การเซ็น signature:
  1) เรียง query params (ยกเว้น sign, access_token) ตาม key
  2) concat = path + (key1+value1) + (key2+value2) + ...
  3) ครอบด้วย app_secret หัวท้าย: base = app_secret + concat + body + app_secret
     (ถ้าไม่มี body ให้ละ body)
  4) sign = HMAC-SHA256(app_secret, base) -> hex (lowercase)

ทุก request แนบ header: x-tts-access-token, content-type
และ query: app_key, timestamp, shop_cipher, sign
"""
import time
import hmac
import hashlib
import json
import requests
from typing import List
from .base import BaseConnector, Order, OrderItem, Product, AdRecord


class TikTokConnector(BaseConnector):
    platform = "tiktok"

    def _sign(self, path: str, params: dict, body: str = "") -> str:
        keys = sorted(k for k in params if k not in ("sign", "access_token"))
        concat = "".join(f"{k}{params[k]}" for k in keys)
        base = f"{self.cfg['app_secret']}{path}{concat}{body}{self.cfg['app_secret']}"
        return hmac.new(
            self.cfg["app_secret"].encode(),
            base.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _call(self, path: str, extra: dict = None, method: str = "GET", body: dict = None) -> dict:
        params = {
            "app_key": self.cfg["app_key"],
            "timestamp": int(time.time()),
            "shop_cipher": self.cfg["shop_cipher"],
        }
        if extra:
            params.update(extra)
        body_str = json.dumps(body) if body else ""
        params["sign"] = self._sign(path, params, body_str)
        headers = {
            "x-tts-access-token": self.cfg["access_token"],
            "content-type": "application/json",
        }
        url = self.cfg["base_url"] + path
        if method == "GET":
            r = requests.get(url, params=params, headers=headers, timeout=30)
        else:
            r = requests.post(url, params=params, headers=headers, data=body_str, timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- Orders ----
    def fetch_orders(self, start: str, end: str) -> List[Order]:
        orders: List[Order] = []
        resp = self._call("/order/202309/orders/search", method="POST", body={
            "create_time_ge": start, "create_time_lt": end, "page_size": 50,
        })
        for o in resp.get("data", {}).get("orders", []):
            items = [OrderItem(
                sku=it.get("seller_sku", ""),
                product_name=it.get("product_name", ""),
                qty=int(it.get("quantity", 1)),
                unit_price=float(it.get("sale_price", 0)),
            ) for it in o.get("line_items", [])]
            orders.append(Order(
                platform=self.platform,
                order_id=o.get("id", ""),
                created_at=o.get("create_time", ""),
                status=o.get("status", "").lower(),
                items=items,
                platform_fee=float(o.get("payment", {}).get("platform_discount", 0)),
            ))
        return orders

    # ---- Products / stock ----
    def fetch_products(self) -> List[Product]:
        prods: List[Product] = []
        resp = self._call("/product/202309/products/search", method="POST",
                          body={"page_size": 100, "status": "ACTIVATE"})
        for p in resp.get("data", {}).get("products", []):
            for sk in p.get("skus", [{}]):
                inv = sk.get("inventory", [{}])
                prods.append(Product(
                    platform=self.platform,
                    sku=sk.get("seller_sku", ""),
                    name=p.get("title", ""),
                    stock=int(inv[0].get("quantity", 0)) if inv else 0,
                    price=float(sk.get("price", {}).get("sale_price", 0)),
                ))
        return prods

    # ---- Ads ----
    def fetch_ads(self, start: str, end: str) -> List[AdRecord]:
        # TikTok Shop Ads API แยกชุด (Marketing API) ต้องขอ scope เพิ่ม
        return []
