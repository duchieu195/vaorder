from datetime import date, datetime
from typing import Optional

import asyncpg
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bot.config import DATABASE_URL
from bot.services.db import get_pool, get_setting

app = FastAPI(title="VAorder Dashboard")
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")


async def _orders_for_month(year: int, month: int):
    pool = await get_pool()
    return await pool.fetch(
        """
        SELECT * FROM orders
        WHERE EXTRACT(year FROM COALESCE(order_date, created_at::date)) = $1
          AND EXTRACT(month FROM COALESCE(order_date, created_at::date)) = $2
        ORDER BY COALESCE(order_date, created_at::date) DESC
        """,
        year, month,
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, month: Optional[str] = None):
    now = datetime.now()
    if month:
        try:
            y, m = int(month.split("-")[0]), int(month.split("-")[1])
        except Exception:
            y, m = now.year, now.month
    else:
        y, m = now.year, now.month

    orders = [dict(o) for o in await _orders_for_month(y, m)]

    rate_str = await get_setting("exchange_rate")
    rate = float(rate_str) if rate_str else 3500.0

    total_cny = sum(float(o["total_cny"]) for o in orders)
    total_vnd = total_cny * rate
    delivered = sum(1 for o in orders if o["delivered_at"])
    with_tracking = sum(1 for o in orders if o["tracking_number"])
    pending = sum(1 for o in orders if not o["tracking_number"])

    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={
            "orders": orders,
            "year": y,
            "month": m,
            "total_cny": total_cny,
            "total_vnd": total_vnd,
            "rate": rate,
            "delivered": delivered,
            "with_tracking": with_tracking,
            "pending": pending,
            "selected_month": f"{y}-{m:02d}",
        },
    )


@app.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail(request: Request, order_id: int):
    pool = await get_pool()
    order = await pool.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
    if not order:
        return HTMLResponse("Không tìm thấy đơn hàng", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="order_detail.html",
        context={"order": dict(order)},
    )


@app.post("/orders/{order_id}/delete")
async def delete_order(order_id: int, request: Request):
    pool = await get_pool()
    await pool.execute("DELETE FROM orders WHERE id = $1", order_id)
    ref = request.headers.get("referer", "/")
    # Quay về trang chủ, giữ nguyên tháng đang xem
    return RedirectResponse(url="/", status_code=303)
async def set_delivered(order_id: int, delivered_at: str = Form(...)):
    try:
        d = date.fromisoformat(delivered_at)
    except ValueError:
        return {"error": "Ngày không hợp lệ"}

    pool = await get_pool()
    await pool.execute(
        "UPDATE orders SET delivered_at = $1 WHERE id = $2",
        d, order_id,
    )
    return RedirectResponse(url=f"/orders/{order_id}", status_code=303)
