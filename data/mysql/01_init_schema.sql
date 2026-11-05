-- =========================================================
-- Business Insights Copilot - MySQL Schema & Seed Data
-- =========================================================

CREATE DATABASE IF NOT EXISTS business_copilot;
USE business_copilot;

-- 1. Customers Table
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS sales_reps;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(120) NOT NULL,
    contact_name VARCHAR(100),
    tier ENUM('Enterprise', 'Mid-Market', 'SMB') NOT NULL DEFAULT 'SMB',
    region ENUM('North America', 'EMEA', 'APAC', 'LATAM') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Sales Representatives
CREATE TABLE sales_reps (
    rep_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    region ENUM('North America', 'EMEA', 'APAC', 'LATAM') NOT NULL,
    quota_amount DECIMAL(12, 2) NOT NULL,
    hire_date DATE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Products
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category ENUM('Software License', 'Cloud Infrastructure', 'Consulting Services', 'Hardware') NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    cost_price DECIMAL(10, 2) NOT NULL,
    status ENUM('Active', 'Discontinued') NOT NULL DEFAULT 'Active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Orders
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    rep_id INT NOT NULL,
    order_date DATE NOT NULL,
    status ENUM('Completed', 'Pending', 'Cancelled', 'Refunded') NOT NULL DEFAULT 'Completed',
    discount_pct DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(50) DEFAULT 'Wire Transfer',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (rep_id) REFERENCES sales_reps(rep_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Order Items
CREATE TABLE order_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- SEED DATA
-- =========================================================

-- Customers
INSERT INTO customers (customer_id, company_name, contact_name, tier, region, created_at) VALUES
(1, 'Apex Financial Corp', 'Sarah Jenkins', 'Enterprise', 'North America', '2023-01-15 10:00:00'),
(2, 'Nexus Health Systems', 'Dr. David Cho', 'Enterprise', 'North America', '2023-02-20 11:30:00'),
(3, 'Berlin Logistics GmbH', 'Markus Bauer', 'Mid-Market', 'EMEA', '2023-03-10 09:15:00'),
(4, 'Tokyo Global Trading', 'Kenji Sato', 'Enterprise', 'APAC', '2023-04-05 14:00:00'),
(5, 'Nordic Renewable AS', 'Astrid Lind', 'Mid-Market', 'EMEA', '2023-05-18 16:45:00'),
(6, 'Sao Paulo Retailers', 'Carlos Silva', 'SMB', 'LATAM', '2023-06-01 12:00:00'),
(7, 'Quantum Data Labs', 'Elena Rostova', 'Mid-Market', 'EMEA', '2023-07-22 08:30:00'),
(8, 'Sydney Analytics Group', 'Liam O\'Connor', 'Enterprise', 'APAC', '2023-08-14 11:10:00');

-- Sales Reps
INSERT INTO sales_reps (rep_id, name, region, quota_amount, hire_date) VALUES
(1, 'Alex Rivera', 'North America', 350000.00, '2022-03-01'),
(2, 'Sophie Martin', 'EMEA', 300000.00, '2022-06-15'),
(3, 'Rohan Sharma', 'APAC', 280000.00, '2023-01-10'),
(4, 'Mariana Gomez', 'LATAM', 150000.00, '2023-04-01');

-- Products
INSERT INTO products (product_id, product_name, category, unit_price, cost_price, status) VALUES
(1, 'Enterprise AI Platform License', 'Software License', 45000.00, 5000.00, 'Active'),
(2, 'Cloud Compute Dedicated Cluster', 'Cloud Infrastructure', 12000.00, 4200.00, 'Active'),
(3, 'Architectural Advisory Sprint', 'Consulting Services', 25000.00, 11000.00, 'Active'),
(4, 'Edge AI Inference Appliance', 'Hardware', 8500.00, 4800.00, 'Active'),
(5, 'Legacy Data Connector Pack', 'Software License', 15000.00, 2000.00, 'Discontinued');

-- Orders (Q3 & Q4 2024 / Q1 2025)
INSERT INTO orders (order_id, customer_id, rep_id, order_date, status, discount_pct, payment_method) VALUES
(101, 1, 1, '2024-10-10', 'Completed', 5.00, 'Wire Transfer'),
(102, 2, 1, '2024-10-25', 'Completed', 0.00, 'Credit Card'),
(103, 3, 2, '2024-11-04', 'Completed', 10.00, 'Wire Transfer'),
(104, 4, 3, '2024-11-15', 'Completed', 0.00, 'Wire Transfer'),
(105, 5, 2, '2024-12-02', 'Completed', 5.00, 'ACH'),
(106, 6, 4, '2024-12-18', 'Refunded', 0.00, 'Credit Card'),
(107, 7, 2, '2024-12-28', 'Completed', 0.00, 'Wire Transfer'),
(108, 8, 3, '2025-01-12', 'Completed', 8.00, 'Wire Transfer'),
(109, 1, 1, '2025-01-20', 'Completed', 0.00, 'Wire Transfer'),
(110, 3, 2, '2025-02-05', 'Pending', 0.00, 'Wire Transfer'),
(111, 4, 3, '2025-02-18', 'Cancelled', 0.00, 'Wire Transfer');

-- Order Items
INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, total_amount) VALUES
-- Order 101: Apex Financial (AI Platform + Cloud Compute)
(1, 101, 1, 2, 45000.00, 90000.00),
(2, 101, 2, 3, 12000.00, 36000.00),
-- Order 102: Nexus Health (Advisory Sprint + Edge Appliance)
(3, 102, 3, 1, 25000.00, 25000.00),
(4, 102, 4, 2, 8500.00, 17000.00),
-- Order 103: Berlin Logistics (AI Platform)
(5, 103, 1, 1, 45000.00, 45000.00),
-- Order 104: Tokyo Global (Edge Inference x4)
(6, 104, 4, 4, 8500.00, 34000.00),
-- Order 105: Nordic Renewable (Cloud Compute x5)
(7, 105, 2, 5, 12000.00, 60000.00),
-- Order 106: Sao Paulo (Refunded Hardware)
(8, 106, 4, 1, 8500.00, 8500.00),
-- Order 107: Quantum Data Labs (Advisory Sprint x2)
(9, 107, 3, 2, 25000.00, 50000.00),
-- Order 108: Sydney Analytics (AI Platform + Advisory)
(10, 108, 1, 1, 45000.00, 45000.00),
(11, 108, 3, 1, 25000.00, 25000.00),
-- Order 109: Apex Financial (Cloud Compute x8)
(12, 109, 2, 8, 12000.00, 96000.00),
-- Order 110: Berlin Logistics (Pending AI Platform)
(13, 110, 1, 1, 45000.00, 45000.00),
-- Order 111: Tokyo Global (Cancelled Advisory)
(14, 111, 3, 1, 25000.00, 25000.00);

