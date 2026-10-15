-- =========================================
-- Workload for Index Tuning
-- =========================================


-- Q1: Search orders by customer
SELECT *
FROM Orders
WHERE customer_id = 5000;


-- Q2: Search orders by status
SELECT *
FROM Orders
WHERE status = 'Pending';


-- Q3: Search orders by date
SELECT *
FROM Orders
WHERE order_date > '2026-01-01';


-- Q4: Search products by category
SELECT *
FROM Product
WHERE category = 'Electronics';


-- Q5: Search products by price
SELECT *
FROM Product
WHERE price > 5000;


-- Q6: Customer and order JOIN
SELECT
    o.order_id,
    c.name,
    o.order_date,
    o.status
FROM Orders o
JOIN Customer c
    ON o.customer_id = c.customer_id
WHERE c.city = 'City 5';


-- Q7: Order items for a particular order
SELECT *
FROM OrderItem
WHERE order_id = 50000;


-- Q8: Products in a particular order
SELECT
    oi.order_id,
    p.product_name,
    oi.quantity,
    oi.price
FROM OrderItem oi
JOIN Product p
    ON oi.product_id = p.product_id
WHERE oi.order_id = 50000;


-- Q9: Group orders by status
SELECT
    status,
    COUNT(*)
FROM Orders
GROUP BY status;


-- Q10: Group products by category
SELECT
    category,
    COUNT(*)
FROM Product
GROUP BY category;


-- Q11: Sort orders by amount
SELECT *
FROM Orders
ORDER BY total_amount DESC
LIMIT 100;


-- Q12: Sort products by price
SELECT *
FROM Product
ORDER BY price DESC
LIMIT 100;


-- Q13: Customer + date filtering
SELECT *
FROM Orders
WHERE customer_id = 5000
AND order_date > '2026-01-01';


-- Q14: Status + date filtering
SELECT *
FROM Orders
WHERE status = 'Pending'
AND order_date > '2026-01-01';


-- Q15: Product category + price filtering
SELECT *
FROM Product
WHERE category = 'Electronics'
AND price > 5000;