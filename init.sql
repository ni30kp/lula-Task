-- Support Copilot Database Initialization Script

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS support_copilot;
USE support_copilot;

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    vip_status BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    total_issues INT DEFAULT 0,
    avg_resolution_time DECIMAL(10, 2)
);

-- Create issues table
CREATE TABLE IF NOT EXISTS issues (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),
    severity ENUM('LOW', 'NORMAL', 'HIGH') DEFAULT 'NORMAL',
    status ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED') DEFAULT 'OPEN',
    priority VARCHAR(50),
    assigned_to VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    resolution_time DECIMAL(10, 2),
    ai_confidence_score DECIMAL(3, 2),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_status (status),
    INDEX idx_severity (severity),
    INDEX idx_created_at (created_at)
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    issue_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    sender_type ENUM('CUSTOMER', 'SUPPORT') NOT NULL,
    sender_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sentiment_score DECIMAL(3, 2),
    FOREIGN KEY (issue_id) REFERENCES issues(id),
    INDEX idx_issue_id (issue_id),
    INDEX idx_created_at (created_at)
);

-- Create recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    issue_id BIGINT NOT NULL,
    template_text TEXT NOT NULL,
    message_type VARCHAR(50),
    tone VARCHAR(50),
    confidence_score DECIMAL(3, 2) NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_count INT DEFAULT 0,
    FOREIGN KEY (issue_id) REFERENCES issues(id),
    INDEX idx_issue_id (issue_id),
    INDEX idx_confidence_score (confidence_score)
);

-- Create conversation_summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    issue_id BIGINT NOT NULL,
    summary TEXT NOT NULL,
    key_points TEXT,
    action_items TEXT,
    sentiment VARCHAR(50),
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id),
    INDEX idx_issue_id (issue_id)
);

-- Create similar_issues table
CREATE TABLE IF NOT EXISTS similar_issues (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_issue_id BIGINT NOT NULL,
    similar_issue_id BIGINT NOT NULL,
    similarity_score DECIMAL(3, 2) NOT NULL,
    similarity_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_issue_id) REFERENCES issues(id),
    FOREIGN KEY (similar_issue_id) REFERENCES issues(id),
    INDEX idx_source_issue_id (source_issue_id),
    INDEX idx_similarity_score (similarity_score)
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'support_executive',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email)
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id BIGINT,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
);

-- Insert sample customers
INSERT INTO customers (email, name, company, vip_status, total_issues, avg_resolution_time) VALUES
('john.doe@acme.com', 'John Doe', 'Acme Corporation', TRUE, 15, 2.5),
('jane.smith@techstart.com', 'Jane Smith', 'TechStart Inc', FALSE, 8, 1.8),
('mike.johnson@globaltech.com', 'Mike Johnson', 'GlobalTech Solutions', TRUE, 25, 3.2),
('sarah.wilson@innovate.com', 'Sarah Wilson', 'Innovate Labs', FALSE, 12, 2.1),
('david.brown@megacorp.com', 'David Brown', 'MegaCorp Industries', TRUE, 30, 4.0);

-- Insert sample issues
INSERT INTO issues (customer_id, title, description, category, severity, status, priority, resolution_time, ai_confidence_score) VALUES
(1, 'Login authentication failed', 'Unable to login to the application. Getting error 401 unauthorized.', 'Authentication', 'HIGH', 'RESOLVED', 'High', 1.5, 0.85),
(1, 'Dashboard not loading', 'Dashboard page shows blank screen after login.', 'UI/UX', 'NORMAL', 'RESOLVED', 'Medium', 2.3, 0.72),
(2, 'API endpoint timeout', 'API calls are timing out after 30 seconds.', 'Performance', 'HIGH', 'IN_PROGRESS', 'High', NULL, 0.91),
(3, 'Data export failing', 'Export functionality is not working for large datasets.', 'Data Processing', 'NORMAL', 'OPEN', 'Medium', NULL, 0.68),
(4, 'Mobile app crash', 'App crashes when accessing user profile section.', 'Mobile', 'HIGH', 'RESOLVED', 'High', 3.8, 0.89),
(5, 'Payment processing error', 'Credit card payments are being declined incorrectly.', 'Payment', 'HIGH', 'OPEN', 'Critical', NULL, 0.94);

-- Insert sample conversations
INSERT INTO conversations (issue_id, message, sender_type, sender_id, sentiment_score) VALUES
(1, 'I cannot login to my account. It says unauthorized.', 'CUSTOMER', 'john.doe@acme.com', -0.8),
(1, 'Thank you for reporting this issue. Let me help you resolve this quickly.', 'SUPPORT', 'support_agent_1', 0.5),
(1, 'I have cleared my browser cache and cookies, but still getting the same error.', 'CUSTOMER', 'john.doe@acme.com', -0.3),
(1, 'Let me check your account status. Can you try logging in now?', 'SUPPORT', 'support_agent_1', 0.7),
(1, 'It works now! Thank you for the help.', 'CUSTOMER', 'john.doe@acme.com', 0.9),
(2, 'The dashboard is completely blank after I login.', 'CUSTOMER', 'jane.smith@techstart.com', -0.6),
(2, 'I understand this is frustrating. Let me investigate the issue.', 'SUPPORT', 'support_agent_2', 0.4),
(2, 'Can you try refreshing the page or using a different browser?', 'SUPPORT', 'support_agent_2', 0.6),
(2, 'Refreshing worked! The dashboard is loading properly now.', 'CUSTOMER', 'jane.smith@techstart.com', 0.8);

-- Insert sample recommendations
INSERT INTO recommendations (issue_id, template_text, message_type, tone, confidence_score, reasoning, used_count) VALUES
(1, 'Thank you for reaching out. I understand you\'re experiencing login issues. Let me help you resolve this quickly.', 'greeting', 'professional', 0.85, 'High confidence due to similar resolved issues', 2),
(1, 'Based on similar cases, this issue can be resolved by clearing browser cache. Would you like me to guide you through the steps?', 'solution', 'helpful', 0.92, 'Similar issue resolved with cache clearing', 1),
(2, 'I see you\'re having trouble with the dashboard. Let me investigate this for you.', 'greeting', 'empathetic', 0.78, 'UI issue pattern detected', 1),
(2, 'This appears to be a loading issue. Can you try refreshing the page?', 'solution', 'helpful', 0.81, 'Common dashboard loading issue', 1);

-- Insert sample users
INSERT INTO users (username, email, hashed_password, role, is_active) VALUES
('admin', 'admin@supportcopilot.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.G', 'admin', TRUE),
('support1', 'support1@supportcopilot.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.G', 'support_executive', TRUE),
('support2', 'support2@supportcopilot.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.G', 'senior_support', TRUE),
('manager', 'manager@supportcopilot.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.G', 'support_manager', TRUE);

-- Insert sample audit logs
INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address) VALUES
(2, 'issue_analyzed', 'issue', 1, '{"severity": "HIGH", "confidence": 0.85}', '192.168.1.100'),
(2, 'recommendation_generated', 'issue', 1, '{"recommendations_count": 3}', '192.168.1.100'),
(3, 'issue_status_updated', 'issue', 2, '{"old_status": "OPEN", "new_status": "RESOLVED"}', '192.168.1.101'),
(4, 'customer_history_viewed', 'customer', 1, '{"total_issues": 15}', '192.168.1.102');

-- Create indexes for better performance
CREATE INDEX idx_issues_customer_severity ON issues(customer_id, severity);
CREATE INDEX idx_issues_status_created ON issues(status, created_at);
CREATE INDEX idx_conversations_issue_sender ON conversations(issue_id, sender_type);
CREATE INDEX idx_recommendations_issue_type ON recommendations(issue_id, message_type);
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action);

-- Create views for common queries
CREATE VIEW issue_summary AS
SELECT 
    i.id,
    i.title,
    i.severity,
    i.status,
    c.name as customer_name,
    c.vip_status,
    i.created_at,
    i.resolution_time,
    COUNT(conv.id) as conversation_count
FROM issues i
JOIN customers c ON i.customer_id = c.id
LEFT JOIN conversations conv ON i.id = conv.issue_id
GROUP BY i.id;

CREATE VIEW customer_analytics AS
SELECT 
    c.id,
    c.name,
    c.email,
    c.vip_status,
    COUNT(i.id) as total_issues,
    AVG(i.resolution_time) as avg_resolution_time,
    COUNT(CASE WHEN i.severity = 'HIGH' THEN 1 END) as critical_issues,
    COUNT(CASE WHEN i.status IN ('RESOLVED', 'CLOSED') THEN 1 END) as resolved_issues
FROM customers c
LEFT JOIN issues i ON c.id = i.customer_id
GROUP BY c.id;

-- Grant permissions
GRANT ALL PRIVILEGES ON support_copilot.* TO 'support_user'@'%';
FLUSH PRIVILEGES; 