import os
import asyncpg

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        database_url = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    return _pool


async def insert_order(product_name, quantity, unit_price_cny, total_cny, order_date, telegram_message_id, order_number=None, tracking_number=None, carrier=None):
    pool = await get_pool()
    return await pool.fetchval(
        """
        INSERT INTO orders (product_name, quantity, unit_price_cny, total_cny, order_date, telegram_message_id, order_number, tracking_number, carrier)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
        """,
        product_name, quantity, unit_price_cny, total_cny, order_date, telegram_message_id, order_number, tracking_number, carrier,
    )


async def update_tracking(order_id, tracking_number, carrier):
    pool = await get_pool()
    await pool.execute(
        "UPDATE orders SET tracking_number = $1, carrier = $2 WHERE id = $3",
        tracking_number, carrier, order_id,
    )


async def update_order_number(order_id, order_number):
    pool = await get_pool()
    await pool.execute(
        "UPDATE orders SET order_number = $1 WHERE id = $2",
        order_number, order_id,
    )


async def update_delivered(order_id, delivered_at):
    pool = await get_pool()
    await pool.execute(
        "UPDATE orders SET delivered_at = $1 WHERE id = $2",
        delivered_at, order_id,
    )


async def get_order(order_id):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)


async def get_pending_orders():
    """Orders without tracking number."""
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM orders WHERE tracking_number IS NULL ORDER BY created_at DESC"
    )


async def get_orders_by_month(year, month):
    pool = await get_pool()
    return await pool.fetch(
        """
        SELECT * FROM orders
        WHERE EXTRACT(year FROM order_date) = $1
          AND EXTRACT(month FROM order_date) = $2
        ORDER BY order_date DESC
        """,
        year, month,
    )


async def get_monthly_summary(year, month):
    pool = await get_pool()
    return await pool.fetchrow(
        """
        SELECT
            COUNT(*)                                                  AS total_orders,
            COALESCE(SUM(total_cny), 0)                              AS total_cny,
            COUNT(*) FILTER (WHERE tracking_number IS NULL)          AS pending,
            COUNT(*) FILTER (WHERE tracking_number IS NOT NULL)      AS with_tracking
        FROM orders
        WHERE EXTRACT(year FROM order_date) = $1
          AND EXTRACT(month FROM order_date) = $2
        """,
        year, month,
    )


async def get_setting(key):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT value FROM settings WHERE key = $1", key)
    return row["value"] if row else None


async def set_setting(key, value):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2",
        key, value,
    )
