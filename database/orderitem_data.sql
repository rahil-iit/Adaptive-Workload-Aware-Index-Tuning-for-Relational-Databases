-- =========================================
-- Generate OrderItem Data
-- =========================================

INSERT INTO OrderItem (
    order_id,
    product_id,
    quantity,
    price
)
SELECT
    1 + floor(random() * 200000)::int,
    1 + floor(random() * 10000)::int,
    1 + floor(random() * 5)::int,
    ROUND((50 + random() * 4950)::numeric, 2)
FROM generate_series(1, 600000);