INSERT INTO users(name,email,role) VALUES ('Admin User','admin@bgcv.local','admin'),('John Smith','john.smith@bgcv.local','employee'),('Sarah Kumar','sarah.kumar@bgcv.local','agent') ON CONFLICT DO NOTHING;
INSERT INTO tickets(ticket_number,title,description,priority,status,created_by) VALUES
('INC0001','VPN Not Connecting','User is unable to connect to the corporate VPN.','HIGH','IN_PROGRESS',2),
('INC0002','Outlook Not Syncing','Mailbox has not synchronized since this morning.','MEDIUM','ASSIGNED',2),
('INC0003','Laptop Unable to Connect to WiFi','Corporate wireless authentication fails.','HIGH','NEW',2),
('INC0004','Production Application Unavailable','Customer-facing application health checks are failing.','CRITICAL','IN_PROGRESS',3),
('INC0005','Microsoft Teams Audio Issue','Microphone is unavailable during calls.','LOW','RESOLVED',2) ON CONFLICT DO NOTHING;
SELECT setval('tickets_id_seq',(SELECT MAX(id) FROM tickets));
INSERT INTO comments(ticket_id,comment,author) VALUES (1,'VPN client was reinstalled.','John Smith'),(1,'Connectivity validation is in progress.','Sarah Kumar');
