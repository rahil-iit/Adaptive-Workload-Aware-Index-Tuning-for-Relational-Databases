-- =========================================
-- Adaptive Workload-Aware Index Tuning
-- Database Schema
-- =========================================

-- Customer table
CREATE TABLE Customer (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(150),
    city VARCHAR(100)
);


-- Supplier table
CREATE TABLE Supplier (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100),
    city VARCHAR(100)
);


-- Product table
CREATE TABLE Product (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150),
    category VARCHAR(100),
    price NUMERIC(10,2),
    supplier_id INT REFERENCES Supplier(supplier_id)
);


-- Orders table
CREATE TABLE Orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES Customer(customer_id),
    order_date DATE,
    status VARCHAR(30),
    total_amount NUMERIC(10,2)
);


-- OrderItem table
CREATE TABLE OrderItem (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES Orders(order_id),
    product_id INT REFERENCES Product(product_id),
    quantity INT,
    price NUMERIC(10,2)
);