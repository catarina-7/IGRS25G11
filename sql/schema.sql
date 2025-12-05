CREATE DATABASE IF NOT EXISTS redial;
USE redial;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  aor VARCHAR(255) UNIQUE NOT NULL,
  contact VARCHAR(512),
  registered BOOL DEFAULT FALSE,
  service_active BOOL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE redial_list (
  id INT AUTO_INCREMENT PRIMARY KEY,
  owner_aor VARCHAR(255) NOT NULL,
  target_aor VARCHAR(255) NOT NULL,
  position INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY owner_target (owner_aor, target_aor)
);

CREATE TABLE metrics (
  id INT AUTO_INCREMENT PRIMARY KEY,
  metric_name VARCHAR(128) NOT NULL,
  metric_value BIGINT DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY (metric_name)
);

INSERT INTO metrics (metric_name, metric_value) VALUES
('total_activations', 0),
('active_users', 0),
('max_redial_list', 0);
