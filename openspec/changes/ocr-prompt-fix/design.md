# Design: OCR Prompt Fix

## Vấn đề cụ thể

Cấu trúc trang tracking thường gồm 2 phần:
- **Phần trên** (cần đọc): thông tin vận đơn — mã tracking, carrier, tên sản phẩm đang giao, giá, số lượng, trạng thái
- **Phần dưới** (bỏ qua): gợi ý sản phẩm tương tự, banner quảng cáo, "猜你喜欢" (Có thể bạn thích)

OCR hiện tại không phân biệt 2 phần này nên đọc nhầm sản phẩm gợi ý.

## Thay đổi prompt

Thêm vào `EXTRACT_TRACKING_PROMPT`:

1. **Mô tả cấu trúc trang** để model biết phần nào cần đọc
2. **Chỉ định rõ** chỉ lấy sản phẩm từ đơn hàng đang vận chuyển (phần trên)
3. **Liệt kê các phần cần bỏ qua**: 猜你喜欢, 为你推荐, 相关推荐, suggested products, recommended items

## Prompt mới

```
Đây là ảnh trang vận đơn / tracking page từ app giao hàng Trung Quốc
(Cainiao, YTO, SF Express, ZTO, JD Logistics, v.v.)

Trang này thường có 2 phần:
- PHẦN TRÊN: thông tin vận đơn — mã tracking, hãng vận chuyển, sản phẩm đang được giao, giá, trạng thái
- PHẦN DƯỚI (BỎ QUA): gợi ý sản phẩm, quảng cáo (猜你喜欢/为你推荐/相关推荐/Recommended)

CHỈ đọc thông tin từ PHẦN TRÊN (đơn hàng đang vận chuyển).
TUYỆT ĐỐI KHÔNG lấy tên sản phẩm từ phần gợi ý/quảng cáo ở cuối trang.

Trích xuất thông tin sau, trả về JSON hợp lệ:
{
  ...fields như cũ...
}
```

## File thay đổi

Chỉ `bot/services/ocr.py` — cập nhật `EXTRACT_TRACKING_PROMPT`.
