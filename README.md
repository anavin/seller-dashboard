# Seller Dashboard — TikTok / Shopee / Lazada

โปรแกรมดึงข้อมูลจาก Official API ของ TikTok Shop, Shopee, Lazada มารวมเป็น **เว็บ Dashboard หน้าเดียว** ที่ดูได้ทั้ง ยอดขาย/ออเดอร์, สินค้า/สต็อก, กำไร/ต้นทุน และ โฆษณา/การตลาด ของทุกร้านรวมกันในที่เดียว

> ตอนนี้ระบบรันด้วย **ข้อมูลตัวอย่าง (sample data)** ได้ทันที เพื่อให้เห็นหน้าตาก่อน แล้วค่อยใส่ API key จริงทีหลัง

---

## 1. ลองรันทันที (โหมดข้อมูลตัวอย่าง)

```bash
cd seller-dashboard
pip install -r requirements.txt
python run.py                      # สร้างไฟล์ docs/dashboard_data.json

# เปิดหน้าเว็บผ่าน local server (สำคัญ — เปิดไฟล์ตรง ๆ จะโหลด json ไม่ได้)
cd docs
python -m http.server 8000
```

แล้วเปิดเบราว์เซอร์ไปที่ **http://localhost:8000** จะเห็น Dashboard พร้อมกราฟครบทุกส่วน

---

## 2. โครงสร้างโปรเจกต์

```
seller-dashboard/
├── run.py                  ← จุดเริ่มต้น สั่ง python run.py
├── config.example.json     ← แม่แบบ config (คัดลอกเป็น config.json แล้วใส่ key จริง)
├── auth.py                 ← ขอ/ต่ออายุ access_token (OAuth) ของแต่ละแพลตฟอร์ม
├── .gitignore              ← กัน config.json (ที่มี key) ไม่ให้ขึ้น GitHub
├── connectors/
│   ├── base.py             ← รูปแบบข้อมูลกลาง (ทุกแพลตฟอร์มแปลงมาเป็นแบบนี้)
│   ├── tiktok.py           ← TikTok Shop Partner API + ลอจิกเซ็น signature
│   ├── shopee.py           ← Shopee Open Platform v2
│   └── lazada.py           ← Lazada Open Platform
├── etl/
│   ├── build.py            ← รวมข้อมูล + คำนวณ KPI ทั้ง 4 กลุ่ม → เขียน json
│   └── sample_data.py      ← ตัวสร้างข้อมูลตัวอย่าง
└── docs/                   ← โฟลเดอร์ที่ GitHub Pages เสิร์ฟ
    ├── index.html          ← หน้าเว็บ Dashboard
    ├── dashboard_data.json ← ข้อมูลที่ run.py สร้าง (อัปเดตทุกครั้งที่รัน)
    └── .nojekyll           ← บอก Pages ไม่ต้องประมวลผล Jekyll
```

---

## เชื่อม API จริงแบบรวดเร็วด้วย auth.py

1. ใส่ `app_key` / `app_secret` (Shopee ใช้ `partner_id` / `partner_key`) ใน `config.json`
2. ตอนสมัคร app ตั้ง **redirect URL = `http://localhost:8000/callback`**
3. รันทีละแพลตฟอร์ม — เบราว์เซอร์จะเปิดให้กดอนุญาต แล้ว token จะเซฟลง config.json อัตโนมัติ
   ```bash
   python auth.py tiktok
   python auth.py shopee
   python auth.py lazada
   ```
4. ต่ออายุ token เมื่อหมดอายุ: `python auth.py refresh shopee`

---

## เผยแพร่ขึ้น GitHub Pages

repo นี้ตั้งให้ Pages เสิร์ฟจากโฟลเดอร์ `docs/` → เปิดใช้งานที่
**Settings → Pages → Source: Deploy from a branch → Branch: `main` / `docs`**
ภายในไม่กี่นาทีจะได้ลิงก์ `https://<username>.github.io/<repo>/`

> ⚠️ repo เป็น **public** = `docs/dashboard_data.json` เปิดให้ทุกคนเห็น
> ถ้าใส่ข้อมูลยอดขายจริง ควรเปลี่ยน repo เป็น private (ต้องใช้ GitHub Pro สำหรับ Pages แบบ private)
> หรือเก็บเฉพาะข้อมูลตัวอย่างไว้บน Pages
>
> อัปเดตข้อมูลบนเว็บ: รัน `python run.py` แล้ว commit `docs/dashboard_data.json` push ขึ้นไป

**หลักการ:** แต่ละแพลตฟอร์มมี API คนละแบบ → `connectors/` แปลงทุกอย่างให้เป็น "รูปแบบกลาง" → `etl/build.py` คำนวณตัวเลข → `dashboard/index.html` แค่เอา json มาวาดกราฟ ทำให้เพิ่มแพลตฟอร์ม/แก้กราฟได้ง่าย

---

## 3. เปลี่ยนมาใช้ข้อมูลจริง

### ขั้นที่ 1 — สมัคร Developer และขอ API key

| แพลตฟอร์ม | สมัครที่ | สิ่งที่ต้องได้ |
|---|---|---|
| **TikTok Shop** | TikTok Shop Partner Center → สร้าง App | `app_key`, `app_secret`, แล้ว authorize ร้านเพื่อได้ `access_token` + `shop_cipher` |
| **Shopee** | Shopee Open Platform | `partner_id`, `partner_key`, authorize ร้านเพื่อได้ `access_token` + `shop_id` |
| **Lazada** | Lazada Open Platform | `app_key`, `app_secret`, authorize ร้านเพื่อได้ `access_token` |

> ทั้ง 3 แพลตฟอร์มใช้ขั้นตอน **OAuth**: เข้าหน้า authorize ของแพลตฟอร์ม → ล็อกอินร้าน → ได้ `code` → เอา code ไปแลก `access_token` (token มีอายุ ต้อง refresh เป็นระยะ)

### ขั้นที่ 2 — ตั้งค่า config

```bash
cp config.example.json config.json
```

แก้ `config.json`: ใส่ key จริง, เปลี่ยน `"enabled": true` ในแพลตฟอร์มที่ใช้ และตั้ง `"use_sample_data": false`

```jsonc
"settings": {
  "lookback_days": 30,        // ดึงข้อมูลย้อนหลังกี่วัน
  "currency": "THB",
  "use_sample_data": false    // ← เปลี่ยนเป็น false เพื่อใช้ API จริง
}
```

### ขั้นที่ 3 — รัน

```bash
python run.py    # ดึงจาก API จริง → อัปเดต dashboard_data.json
```

> **หมายเหตุ:** โค้ดใน `connectors/*.py` วาง endpoint และลอจิกเซ็น signature ของแต่ละแพลตฟอร์มไว้ให้แล้ว แต่ field name / รูปแบบวันที่ ของแต่ละ API อาจปรับเล็กน้อยตามเวอร์ชันล่าสุด — เทียบกับเอกสารทางการตอนเชื่อมจริงได้เลย จุดที่ต้องเช็กคือฟังก์ชัน `fetch_orders`, `fetch_products`, `fetch_ads`

---

## 4. ตัวเลขที่ Dashboard แสดง

**ยอดขาย & ออเดอร์** — ยอดขายรวม, จำนวนออเดอร์, จำนวนชิ้น, AOV, อัตรายกเลิก/คืน, กราฟยอดขายรายวันแยกแพลตฟอร์ม, สัดส่วนยอดขายตามช่องทาง

**กำไร & ต้นทุน** — กำไรขั้นต้น, กำไรสุทธิ (หักต้นทุน + ค่าธรรมเนียม + ค่าโฆษณา), อัตรากำไร, ตารางสินค้าขายดี + กำไรราย SKU, กราฟโครงสร้างกำไร

**โฆษณา & การตลาด** — ค่าโฆษณา, ยอดขายจากโฆษณา, ROAS, CTR, CVR, CPC, เปรียบเทียบประสิทธิภาพแต่ละช่องทาง

**สินค้า & สต็อก** — จำนวน SKU, สินค้าหมดสต็อก, สินค้าใกล้หมด, ตารางแจ้งเตือนสต็อกต่ำแยกรายแพลตฟอร์ม

---

## 5. ใส่ต้นทุนสินค้าเอง (สำหรับกำไรที่แม่นยำ)

API ของแพลตฟอร์มให้ "ราคาขาย" แต่ไม่รู้ "ต้นทุน" ของคุณ — แก้ค่า `unit_cost` / `cost` ได้ที่ catalog ใน `etl/sample_data.py` (โหมดตัวอย่าง) หรือทำไฟล์ `costs.csv` (sku, cost) แล้ว map เข้าตอน ETL เมื่อใช้ข้อมูลจริง

---

## 6. ตั้งให้อัปเดตอัตโนมัติ (ออปชัน)

ตั้ง cron / Task Scheduler ให้รัน `python run.py` ทุกเช้า เช่น
```
0 7 * * *  cd /path/seller-dashboard && python run.py
```
หน้าเว็บกดปุ่ม Reload ก็เห็นข้อมูลล่าสุดทันที
