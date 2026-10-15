-- =========================================
-- Generate Sample Data
-- Adaptive Workload-Aware Index Tuning
-- =========================================


-- =========================================
-- 1. Customers
-- =========================================

INSERT INTO Customer (name, email, city)
SELECT
    'Customer ' || i,
    'customer' || i || '@example.com',
    'City ' || (i % 20)
FROM generate_series(1, 20000) AS i;


-- =========================================
-- 2. Suppliers
-- =========================================

INSERT INTO Supplier (supplier_name, city)
SELECT
    'Supplier ' || i,
    'City ' || (i % 20)
FROM generate_series(1, 1000) AS i;


-- =========================================
-- 3. Products
-- =========================================

INSERT INTO Product (
    product_name,
    category,
    price,
    supplier_id
)
SELECT
    'Product ' || i,
    CASE
        WHEN i % 5 = 0 THEN 'Electronics'
        WHEN i % 5 = 1 THEN 'Clothing'
        WHEN i % 5 = 2 THEN 'Books'
        WHEN i % 5 = 3 THEN 'Home'
        ELSE 'Sports'
    END,
    ROUND((100 + random() * 9900)::numeric, 2),
    1 + ((i - 1) % 1000)
FROM generate_series(1, 10000) AS i;


-- =========================================
-- 4. Orders
-- =========================================

INSERT INTO Orders (
    customer_id,
    order_date,
    status,
    total_amount
)
SELECT
    1 + floor(random() * 20000)::int,
    DATE '2024-01-01' + floor(random() * 1000)::int,
    CASE
        WHEN i % 5 = 0 THEN 'Pending'
        WHEN i % 5 = 1 THEN 'Processing'
        WHEN i % 5 = 2 THEN 'Shipped'
        WHEN i % 5 = 3 THEN 'Delivered'
        ELSE 'Cancelled'
    END,
    ROUND((100 + random() * 4900)::numeric, 2)
FROM generate_series(1, 200000) AS i;