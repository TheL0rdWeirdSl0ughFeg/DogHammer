CREATE SCHEMA IF NOT EXISTS manage_server
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE manage_server;

CREATE TABLE IF NOT EXISTS users (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    firstname VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('USER', 'ADMIN', 'SUPERADMIN') NOT NULL,
    enabled BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS portal_sessions (
    user_id INT UNSIGNED PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE,
    created_at DATETIME NOT NULL,
    last_seen DATETIME NOT NULL,
    state ENUM('ACTIVE', 'LOGGED_OUT', 'EXPIRED', 'LOCKED') NOT NULL,
    login_gen INT UNSIGNED NOT NULL DEFAULT 0,
    last_login_ip VARCHAR(64),
    last_login_device TEXT,

    INDEX idx_portal_last_seen (last_seen),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS session_registry (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS service (
    token VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    service_type ENUM('REGION', 'PRIVILEGE') NOT NULL,
    service_name ENUM(
        'GAMES',
        'FILES',
        'FORUM',
        'ADMIN',
        'BACKEND'
    ) NOT NULL,
    issued_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,

    INDEX idx_service_session (session_id),
    INDEX idx_service_expires (expires_at),

    FOREIGN KEY (session_id)
        REFERENCES portal_sessions(session_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS activity_log (
    event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    service_type VARCHAR(64),
    service_name VARCHAR(64),
    metadata TEXT,

    INDEX idx_activity_session (session_id, timestamp),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
) ENGINE=InnoDB;