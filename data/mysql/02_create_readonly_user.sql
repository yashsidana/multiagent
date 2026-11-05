-- =========================================================
-- Business Insights Copilot - Read-Only Security Script
-- =========================================================

-- Create dedicated read-only role user
CREATE USER IF NOT EXISTS 'copilot_readonly'@'%' IDENTIFIED BY 'readonly_pass';

-- Grant solely SELECT privileges on the business_copilot schema
GRANT SELECT ON business_copilot.* TO 'copilot_readonly'@'%';

-- Flush privileges to apply changes immediately
FLUSH PRIVILEGES;

