CREATE TABLE orders (
    id                    SERIAL PRIMARY KEY,
    product_name          TEXT NOT NULL,
    quantity              INTEGER NOT NULL,
    unit_price_cny        NUMERIC(10,2),
    total_cny             NUMERIC(10,2) NOT NULL,
    order_date            DATE,
    tracking_number       VARCHAR(100),
    carrier               VARCHAR(50),
    delivered_at          DATE,
    telegram_message_id   BIGINT,
    created_at            TIMESTAMP DEFAULT NOW()
);

CREATE TABLE settings (
    key   VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX idx_orders_order_date    ON orders(order_date);
CREATE INDEX idx_orders_tracking      ON orders(tracking_number);
CREATE INDEX idx_orders_delivered_at  ON orders(delivered_at);
CREATE INDEX idx_orders_created_at    ON orders(created_at);

INSERT INTO settings (key, value) VALUES ('exchange_rate', '3500');
