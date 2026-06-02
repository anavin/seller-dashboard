"""
ETL: รวมข้อมูลจากทุกแพลตฟอร์ม -> เขียน docs/dashboard_data.json
ส่งข้อมูลระดับ "ออเดอร์" (granular) ลงไป แล้วให้หน้าเว็บคำนวณ KPI/กราฟสดตามฟิลเตอร์
ทำให้ slice ได้ทุกมิติ: ช่วงเวลา / แพลตฟอร์ม / หมวดหมู่ / สถานะ / ภูมิภาค / ชั่วโมง / ลูกค้า
"""
import json
import os
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect(cfg):
    from connectors import REGISTRY
    days = cfg["settings"].get("lookback_days", 60)
    if cfg["settings"].get("use_sample_data", True):
        from etl import sample_data as s
        return s.gen_orders(days), s.gen_products(), s.gen_ads(days)

    orders, products, ads = [], [], []
    start, end = "", ""  # ผู้ใช้ปรับ format ช่วงเวลาให้ตรงแต่ละ API ในขั้น production
    for name, conn_cls in REGISTRY.items():
        pc = cfg.get(name, {})
        if not pc.get("enabled"):
            continue
        c = conn_cls(pc)
        orders += c.fetch_orders(start, end)
        products += c.fetch_products()
        ads += c.fetch_ads(start, end)
    return orders, products, ads


def build(cfg):
    orders, products, ads = collect(cfg)
    cur = cfg["settings"].get("currency", "THB")

    # ---- orders แบบ granular ----
    order_rows = []
    for o in orders:
        order_rows.append({
            "date": o.created_at, "hour": o.hour, "platform": o.platform,
            "status": o.status, "region": o.region, "customer": o.customer_type,
            "shipping_fee": round(o.shipping_fee, 2),
            "platform_fee": round(o.platform_fee, 2),
            "items": [{
                "sku": i.sku, "name": i.product_name, "category": i.category,
                "qty": i.qty, "price": round(i.unit_price, 2),
                "cost": round(i.unit_cost, 2),
            } for i in o.items],
        })

    # ---- products: รวมสต็อกแยกแพลตฟอร์มต่อ sku ----
    pmap = {}
    for p in products:
        rec = pmap.setdefault(p.sku, {
            "sku": p.sku, "name": p.name, "category": p.category,
            "price": round(p.price, 2), "cost": round(p.cost, 2),
            "stock": {"tiktok": 0, "shopee": 0, "lazada": 0},
        })
        rec["stock"][p.platform] = p.stock

    # ---- ads ----
    ad_rows = [{
        "date": a.date, "platform": a.platform, "campaign": a.campaign,
        "spend": round(a.spend, 2), "impressions": a.impressions,
        "clicks": a.clicks, "orders": a.orders, "revenue": round(a.revenue, 2),
    } for a in ads]

    dates = sorted({o.created_at for o in orders})
    cats = sorted({i.category for o in orders for i in o.items if i.category})
    regions = sorted({o.region for o in orders if o.region})

    data = {
        "meta": {
            "currency": cur,
            "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "start_date": dates[0] if dates else "",
            "end_date": dates[-1] if dates else "",
            "days": len(dates),
            "platforms": ["tiktok", "shopee", "lazada"],
            "categories": cats,
            "regions": regions,
        },
        "orders": order_rows,
        "products": list(pmap.values()),
        "ads": ad_rows,
    }
    return data


def main():
    cfg_path = os.path.join(BASE, "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(BASE, "config.example.json")
        print("⚠️  ไม่พบ config.json ใช้ config.example.json (โหมด sample data)")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    data = build(cfg)
    out = os.path.join(BASE, "docs", "dashboard_data.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = os.path.getsize(out) / 1024
    print(f"✅ เขียนข้อมูลแล้ว: {out}  ({size_kb:.0f} KB)")
    print(f"   {len(data['orders'])} ออเดอร์ | {len(data['products'])} SKU | "
          f"{len(data['ads'])} แถวโฆษณา | {data['meta']['days']} วัน")


if __name__ == "__main__":
    main()
