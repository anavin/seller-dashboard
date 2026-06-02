from .tiktok import TikTokConnector
from .shopee import ShopeeConnector
from .lazada import LazadaConnector

REGISTRY = {
    "tiktok": TikTokConnector,
    "shopee": ShopeeConnector,
    "lazada": LazadaConnector,
}
