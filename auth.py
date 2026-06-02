"""
auth.py — ตัวช่วยขอ access_token (OAuth) ของ TikTok Shop / Shopee / Lazada
ทำสเตป 2-4 ให้อัตโนมัติ: สร้างลิงก์ authorize -> รับ code -> แลก token -> เซฟลง config.json

วิธีใช้:
    python auth.py tiktok      # ขอ token ของ TikTok Shop
    python auth.py shopee
    python auth.py lazada
    python auth.py refresh tiktok   # ต่ออายุ token

ก่อนใช้: ใส่ app_key/app_secret (หรือ partner_id/partner_key) ใน config.json ให้ครบก่อน
และตั้ง redirect URL ตอนสมัคร app ให้ตรงกับ REDIRECT ด้านล่าง
"""
import sys
import json
import time
import hmac
import hashlib
import threading
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

REDIRECT_HOST = "localhost"
REDIRECT_PORT = 8000
REDIRECT = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/callback"

CONFIG = "config.json"
_captured = {}


# ---------- เว็บเซิร์ฟเวอร์เล็ก ๆ รับ code ที่แพลตฟอร์มเด้งกลับมา ----------
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path)
        if q.path != "/callback":
            self.send_response(404); self.end_headers(); return
        params = urllib.parse.parse_qs(q.query)
        _captured.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>✅ รับ code แล้ว กลับไปที่เทอร์มินัลได้เลย</h2>"
                         "<p>ปิดแท็บนี้ได้</p>".encode("utf-8"))

    def log_message(self, *a):  # ปิด log รก ๆ
        pass


def wait_for_code(timeout=300):
    _captured.clear()
    srv = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), _Handler)
    t = threading.Thread(target=srv.handle_request)  # รับครั้งเดียวพอ
    t.start()
    print(f"⏳ รอ authorize ในเบราว์เซอร์… (redirect = {REDIRECT})")
    t.join(timeout)
    srv.server_close()
    if "code" not in _captured:
        raise SystemExit("❌ ไม่ได้รับ code — ลองใหม่ และเช็ค redirect URL ใน app ให้ตรง")
    return _captured


def load_cfg():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"💾 บันทึก token ลง {CONFIG} แล้ว")


# ====================== TikTok Shop ======================
def tiktok_auth(cfg):
    c = cfg["tiktok"]
    # ลิงก์ authorize อยู่ในหน้า App ของคุณใน Partner Center (service_id เฉพาะ app)
    # ใส่ service_id ของ app ลงใน config ถ้ามี ไม่งั้นเปิดจาก Partner Center เองแล้ววาง code
    auth_url = c.get("auth_url")
    if auth_url:
        webbrowser.open(auth_url)
        data = wait_for_code()
        code = data["code"]
    else:
        code = input("วาง auth_code จาก TikTok Partner Center: ").strip()

    r = requests.get("https://auth.tiktok-shops.com/api/v2/token/get", params={
        "app_key": c["app_key"], "app_secret": c["app_secret"],
        "auth_code": code, "grant_type": "authorized_code",
    }, timeout=30)
    d = r.json().get("data", {})
    c["access_token"] = d.get("access_token", "")
    c["refresh_token"] = d.get("refresh_token", "")
    # ดึง shop_cipher ของร้านที่ได้รับสิทธิ์
    shops = _tiktok_get_shops(c)
    if shops:
        c["shop_cipher"] = shops[0].get("cipher", "")
        c["shop_id"] = shops[0].get("id", "")
        print(f"🏪 ร้าน: {shops[0].get('name','')} (cipher set)")
    c["enabled"] = True
    return cfg


def _tiktok_get_shops(c):
    path = "/authorization/202309/shops"
    ts = int(time.time())
    params = {"app_key": c["app_key"], "timestamp": ts}
    keys = sorted(params)
    concat = "".join(f"{k}{params[k]}" for k in keys)
    base = f"{c['app_secret']}{path}{concat}{c['app_secret']}"
    params["sign"] = hmac.new(c["app_secret"].encode(), base.encode(),
                              hashlib.sha256).hexdigest()
    r = requests.get(c["base_url"] + path, params=params,
                     headers={"x-tts-access-token": c["access_token"]}, timeout=30)
    return r.json().get("data", {}).get("shops", [])


def tiktok_refresh(cfg):
    c = cfg["tiktok"]
    r = requests.get("https://auth.tiktok-shops.com/api/v2/token/refresh", params={
        "app_key": c["app_key"], "app_secret": c["app_secret"],
        "refresh_token": c["refresh_token"], "grant_type": "refresh_token",
    }, timeout=30)
    d = r.json().get("data", {})
    c["access_token"] = d.get("access_token", c["access_token"])
    c["refresh_token"] = d.get("refresh_token", c["refresh_token"])
    return cfg


# ====================== Shopee ======================
def _shopee_sign(partner_id, partner_key, path, timestamp):
    base = f"{partner_id}{path}{timestamp}"
    return hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()


def shopee_auth(cfg):
    c = cfg["shopee"]
    path = "/api/v2/shop/auth_partner"
    ts = int(time.time())
    sign = _shopee_sign(c["partner_id"], c["partner_key"], path, ts)
    auth_url = (c["base_url"] + path + "?" + urllib.parse.urlencode({
        "partner_id": c["partner_id"], "timestamp": ts,
        "sign": sign, "redirect": REDIRECT,
    }))
    webbrowser.open(auth_url)
    data = wait_for_code()
    code = data["code"]
    if "shop_id" in data:
        c["shop_id"] = int(data["shop_id"])

    # แลก token
    tpath = "/api/v2/auth/token/get"
    ts2 = int(time.time())
    sign2 = _shopee_sign(c["partner_id"], c["partner_key"], tpath, ts2)
    r = requests.post(c["base_url"] + tpath, params={
        "partner_id": c["partner_id"], "timestamp": ts2, "sign": sign2,
    }, json={"code": code, "shop_id": c["shop_id"], "partner_id": c["partner_id"]},
        timeout=30)
    d = r.json()
    c["access_token"] = d.get("access_token", "")
    c["refresh_token"] = d.get("refresh_token", "")
    c["enabled"] = True
    return cfg


def shopee_refresh(cfg):
    c = cfg["shopee"]
    path = "/api/v2/auth/access_token/get"
    ts = int(time.time())
    sign = _shopee_sign(c["partner_id"], c["partner_key"], path, ts)
    r = requests.post(c["base_url"] + path, params={
        "partner_id": c["partner_id"], "timestamp": ts, "sign": sign,
    }, json={"refresh_token": c["refresh_token"], "shop_id": c["shop_id"],
             "partner_id": c["partner_id"]}, timeout=30)
    d = r.json()
    c["access_token"] = d.get("access_token", c["access_token"])
    c["refresh_token"] = d.get("refresh_token", c["refresh_token"])
    return cfg


# ====================== Lazada ======================
def _lazada_sign(secret, path, params):
    ordered = "".join(f"{k}{params[k]}" for k in sorted(params))
    base = path + ordered
    return hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest().upper()


def lazada_auth(cfg):
    c = cfg["lazada"]
    auth_url = "https://auth.lazada.com/oauth/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "force_auth": "true",
        "redirect_uri": REDIRECT, "client_id": c["app_key"],
    })
    webbrowser.open(auth_url)
    data = wait_for_code()
    code = data["code"]

    path = "/auth/token/create"
    params = {
        "app_key": c["app_key"], "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256", "code": code,
    }
    params["sign"] = _lazada_sign(c["app_secret"], path, params)
    r = requests.get("https://auth.lazada.com/rest" + path, params=params, timeout=30)
    d = r.json()
    c["access_token"] = d.get("access_token", "")
    c["refresh_token"] = d.get("refresh_token", "")
    # endpoint รายประเทศ (เช่น .co.th) อยู่ใน country_user_info
    c["enabled"] = True
    return cfg


def lazada_refresh(cfg):
    c = cfg["lazada"]
    path = "/auth/token/refresh"
    params = {
        "app_key": c["app_key"], "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256", "refresh_token": c["refresh_token"],
    }
    params["sign"] = _lazada_sign(c["app_secret"], path, params)
    r = requests.get("https://auth.lazada.com/rest" + path, params=params, timeout=30)
    d = r.json()
    c["access_token"] = d.get("access_token", c["access_token"])
    c["refresh_token"] = d.get("refresh_token", c["refresh_token"])
    return cfg


AUTH = {"tiktok": tiktok_auth, "shopee": shopee_auth, "lazada": lazada_auth}
REFRESH = {"tiktok": tiktok_refresh, "shopee": shopee_refresh, "lazada": lazada_refresh}


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cfg = load_cfg()
    if sys.argv[1] == "refresh":
        plat = sys.argv[2]
        cfg = REFRESH[plat](cfg)
        save_cfg(cfg)
        print(f"🔄 ต่ออายุ token ของ {plat} แล้ว")
        return
    plat = sys.argv[1]
    if plat not in AUTH:
        print("ใช้: python auth.py [tiktok|shopee|lazada]"); return
    cfg = AUTH[plat](cfg)
    save_cfg(cfg)
    print(f"✅ ขอ token ของ {plat} สำเร็จ — รัน python run.py เพื่อดึงข้อมูลได้เลย")


if __name__ == "__main__":
    main()
