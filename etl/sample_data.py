"""
สร้างข้อมูลตัวอย่าง (mock) ให้ dashboard ทำงานได้ทันทีโดยยังไม่ต้องมี API จริง
มีหลายมิติเพื่อให้ slice ได้ครบ: หมวดหมู่ / ภูมิภาค / ชั่วโมง / ประเภทลูกค้า / สถานะ
สร้าง 60 วันเพื่อให้เทียบ "ช่วงก่อนหน้า" ได้
"""
import random
from datetime import date, timedelta
from connectors.base import Order, OrderItem, Product, AdRecord

random.seed(7)

PLATFORMS = ["tiktok", "shopee", "lazada"]
# (sku, ชื่อ, ราคาขาย, ต้นทุน, หมวดหมู่)
CATALOG = [
    ("SKU-001", "เซรั่มบำรุงผิว 30ml", 390, 150, "สกินแคร์"),
    ("SKU-002", "ครีมกันแดด SPF50", 290, 110, "สกินแคร์"),
    ("SKU-003", "โฟมล้างหน้า 100g", 159, 55, "สกินแคร์"),
    ("SKU-004", "มาส์กหน้า (กล่อง 10 แผ่น)", 249, 90, "สกินแคร์"),
    ("SKU-005", "ลิปบาล์ม", 99, 30, "เมคอัพ"),
    ("SKU-006", "วิตามินซี 1000mg", 450, 180, "อาหารเสริม"),
    ("SKU-007", "ครีมบำรุงกลางคืน", 520, 200, "สกินแคร์"),
    ("SKU-008", "สเปรย์น้ำแร่", 199, 70, "สกินแคร์"),
    ("SKU-009", "แปรงแต่งหน้าเซ็ต 5 ชิ้น", 350, 120, "อุปกรณ์"),
    ("SKU-010", "คอลลาเจนชง", 590, 230, "อาหารเสริม"),
]
REGIONS = ["กรุงเทพฯ", "ภาคกลาง", "ภาคเหนือ", "ภาคอีสาน", "ภาคใต้", "ภาคตะวันออก"]
REGION_W = [34, 20, 13, 18, 9, 6]
CANCEL_RATE = {"tiktok": 0.06, "shopee": 0.05, "lazada": 0.07}
FEE_RATE = {"tiktok": 0.08, "shopee": 0.09, "lazada": 0.085}
# น้ำหนักการสั่งซื้อตามชั่วโมง (พีคช่วงเย็น-ค่ำ)
HOUR_W = ([1]*8 + [2,3,4,4,5,4,3,3,4,5,7,9,10,9,7,4])


def _weighted_hour():
    return random.choices(range(24), weights=HOUR_W)[0]


def gen_orders(days: int = 60):
    orders = []
    oid = 1000
    for d in range(days):
        day = (date.today() - timedelta(days=days - 1 - d)).isoformat()
        dow = (date.today() - timedelta(days=days - 1 - d)).weekday()
        # weekend boost + trend ค่อยๆ โต
        weekend = 1.25 if dow >= 5 else 1.0
        base_orders = int((16 + d * 0.25 + random.randint(-4, 7)) * weekend)
        for _ in range(max(base_orders, 0)):
            plat = random.choices(PLATFORMS, weights=[40, 38, 22])[0]
            n_items = random.choices([1, 2, 3], weights=[68, 24, 8])[0]
            items = []
            for _ in range(n_items):
                sku, name, price, cost, cat = random.choice(CATALOG)
                qty = random.choices([1, 2, 3], weights=[82, 14, 4])[0]
                items.append(OrderItem(sku=sku, product_name=name, qty=qty,
                                       unit_price=price, unit_cost=cost, category=cat))
            gross = sum(i.qty * i.unit_price for i in items)
            status = "completed"
            if random.random() < CANCEL_RATE[plat]:
                status = random.choice(["cancelled", "returned"])
            orders.append(Order(
                platform=plat, order_id=f"{plat[:2].upper()}{oid}",
                created_at=day, status=status, items=items,
                shipping_fee=round(random.choice([0, 0, 30, 40]), 2),
                platform_fee=round(gross * FEE_RATE[plat], 2),
                hour=_weighted_hour(),
                region=random.choices(REGIONS, weights=REGION_W)[0],
                customer_type=random.choices(["new", "returning"], weights=[58, 42])[0],
            ))
            oid += 1
    return orders


def gen_products():
    prods = []
    low_skus = {"SKU-005", "SKU-008"}
    out_skus = {"SKU-003"}
    for plat in PLATFORMS:
        for sku, name, price, cost, cat in CATALOG:
            if sku in out_skus:
                stock = 0
            elif sku in low_skus:
                stock = random.randint(0, 8)
            else:
                stock = random.randint(20, 130)
            prods.append(Product(
                platform=plat, sku=sku, name=name, stock=stock,
                price=price, cost=cost, status="active", category=cat,
            ))
    return prods


def gen_ads(days: int = 60):
    ads = []
    campaigns = {
        "tiktok": ["TikTok Video Ads", "TikTok LIVE Ads"],
        "shopee": ["Shopee Search Ads", "Shopee Discovery Ads"],
        "lazada": ["Lazada Sponsored Search"],
    }
    for d in range(days):
        day = (date.today() - timedelta(days=days - 1 - d)).isoformat()
        for plat in PLATFORMS:
            for camp in campaigns[plat]:
                spend = round(random.uniform(120, 480), 2)
                roas = random.uniform(2.5, 5.5)
                revenue = round(spend * roas, 2)
                aov = random.uniform(250, 450)
                orders = max(int(revenue / aov), 1)
                cvr = random.uniform(0.03, 0.08)
                clicks = int(orders / cvr)
                ctr = random.uniform(0.012, 0.035)
                imps = int(clicks / ctr)
                ads.append(AdRecord(
                    platform=plat, date=day, campaign=camp,
                    spend=spend, impressions=imps, clicks=clicks,
                    orders=orders, revenue=revenue,
                ))
    return ads
