import base64
import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_api_key = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
_base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
_API_ENDPOINT = f"{_base_url.rstrip('/')}/v1/messages"
_HEADERS = {
    "x-api-key": _api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

EXTRACT_PROMPT = """Đây là ảnh đơn hàng từ Tmall hoặc Taobao (Trung Quốc).

Hãy trích xuất thông tin sau và trả về JSON hợp lệ:
{
  "order_number": "mã đơn hàng hoặc null nếu không có",
  "product_name": "tên sản phẩm dịch sang tiếng Việt",
  "quantity": số_lượng_nguyên,
  "unit_price_cny": đơn_giá_CNY_số_thực,
  "total_cny": tổng_tiền_CNY_số_thực,
  "order_date": "YYYY-MM-DD hoặc null nếu không rõ"
}

Quy tắc:
- order_number: mã đơn hàng (dãy số dài, thường bắt đầu bằng số, ví dụ: 123456789012345678); null nếu không tìm thấy
- product_name: dịch tên sản phẩm sang tiếng Việt, ngắn gọn
- quantity: số nguyên, mặc định 1 nếu không có
- unit_price_cny: đơn giá mỗi sản phẩm; nếu không có thì tính = total_cny / quantity
- total_cny: tổng tiền phải trả (bắt buộc)
- order_date: ngày đặt hàng định dạng YYYY-MM-DD

Chỉ trả về JSON, không giải thích thêm."""


EXTRACT_TRACKING_PROMPT = """Đây là ảnh trang vận đơn / tracking page từ app giao hàng Trung Quốc
(Cainiao, YTO, SF Express, ZTO, JD Logistics, v.v.)

Trích xuất thông tin sau, trả về JSON hợp lệ:
{
  "tracking_number": "mã vận đơn (dãy số/chữ số dài) hoặc null",
  "carrier": "tên viết tắt: YTO/SF/ZTO/JD/4PX/YUNDA/STO/BEST/EMS hoặc null",
  "product_name": "tên sản phẩm dịch sang tiếng Việt, ngắn gọn",
  "quantity": số_nguyên,
  "unit_price_cny": đơn_giá_hoặc_null,
  "total_cny": tổng_tiền_CNY_hoặc_null,
  "order_number": "mã đơn hàng Tmall/Taobao nếu có, null nếu không thấy",
  "delivered_at": "YYYY-MM-DD nếu trạng thái là đã giao hàng (已签收/Delivered), null nếu chưa giao"
}

Carrier mapping:
- 菜鸟速递, 圆通, YTO → YTO
- 顺丰速运, SF → SF
- 中通快递, ZTO → ZTO
- 京东物流, JD → JD
- 百世快递, BEST → BEST
- 韵达快递, YUNDA → YUNDA
- 申通快递, STO → STO
- 4PX → 4PX
- 邮政, EMS → EMS

Chỉ trả về JSON, không giải thích."""


def _call_vision_api(image_path: str, prompt: str) -> dict | None:
    image_data = base64.standard_b64encode(Path(image_path).read_bytes()).decode()
    ext = Path(image_path).suffix.lower()
    media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_type_map.get(ext, "image/jpeg")

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": prompt},
            ],
        }],
    }

    resp = httpx.post(_API_ENDPOINT, headers=_HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"]
    logger.info("OCR raw response: %s", text)

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("JSON parse error: %s | raw: %s", e, text)
        return None


def extract_tracking_from_image(image_path: str) -> dict | None:
    data = _call_vision_api(image_path, EXTRACT_TRACKING_PROMPT)
    if not data:
        return None
    delivered_at = None
    if data.get("delivered_at"):
        try:
            from datetime import date as _date
            delivered_at = _date.fromisoformat(data["delivered_at"])
        except (ValueError, TypeError):
            pass
    return {
        "tracking_number": data["tracking_number"].replace(" ", "").strip() if data.get("tracking_number") else None,
        "carrier": data.get("carrier") or None,
        "order_number": data.get("order_number") or None,
        "product_name": data.get("product_name") or "Sản phẩm không rõ",
        "quantity": int(data.get("quantity") or 1),
        "unit_price_cny": float(data["unit_price_cny"]) if data.get("unit_price_cny") else None,
        "total_cny": float(data["total_cny"]) if data.get("total_cny") else None,
        "delivered_at": delivered_at,
    }


def extract_order_from_image(image_path: str) -> dict | None:
    data = _call_vision_api(image_path, EXTRACT_PROMPT)
    if not data or not data.get("total_cny"):
        return None
    return {
        "order_number": data.get("order_number"),
        "product_name": data.get("product_name", "Sản phẩm không rõ"),
        "quantity": int(data.get("quantity") or 1),
        "unit_price_cny": float(data.get("unit_price_cny") or 0),
        "total_cny": float(data["total_cny"]),
        "order_date": data.get("order_date"),
    }
