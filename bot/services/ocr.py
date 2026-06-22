import base64
import json
import os
from pathlib import Path

import anthropic

_client = None


def _get_client():
    global _client
    if _client is None:
        from bot.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL
        kwargs = {"api_key": ANTHROPIC_API_KEY}
        if ANTHROPIC_BASE_URL:
            kwargs["base_url"] = ANTHROPIC_BASE_URL
        _client = anthropic.Anthropic(**kwargs)
    return _client


EXTRACT_PROMPT = """Đây là ảnh đơn hàng từ Tmall hoặc Taobao (Trung Quốc).

Hãy trích xuất thông tin sau và trả về JSON hợp lệ:
{
  "product_name": "tên sản phẩm dịch sang tiếng Việt",
  "quantity": số_lượng_nguyên,
  "unit_price_cny": đơn_giá_CNY_số_thực,
  "total_cny": tổng_tiền_CNY_số_thực,
  "order_date": "YYYY-MM-DD hoặc null nếu không rõ"
}

Quy tắc:
- product_name: dịch tên sản phẩm sang tiếng Việt, ngắn gọn
- quantity: số nguyên, mặc định 1 nếu không có
- unit_price_cny: đơn giá mỗi sản phẩm; nếu không có thì tính = total_cny / quantity
- total_cny: tổng tiền phải trả (bắt buộc)
- order_date: ngày đặt hàng định dạng YYYY-MM-DD

Chỉ trả về JSON, không giải thích thêm."""


def extract_order_from_image(image_path: str) -> dict | None:
    image_data = base64.standard_b64encode(Path(image_path).read_bytes()).decode()

    ext = Path(image_path).suffix.lower()
    media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_type_map.get(ext, "image/jpeg")

    client = _get_client()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": EXTRACT_PROMPT},
            ],
        }],
    )

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return None

    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    data = json.loads(text)

    # Validate minimum required field
    if not data.get("total_cny"):
        return None

    return {
        "product_name": data.get("product_name", "Sản phẩm không rõ"),
        "quantity": int(data.get("quantity") or 1),
        "unit_price_cny": float(data.get("unit_price_cny") or 0),
        "total_cny": float(data["total_cny"]),
        "order_date": data.get("order_date"),
    }
