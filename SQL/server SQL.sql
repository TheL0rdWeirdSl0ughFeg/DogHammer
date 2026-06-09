CREATE SCHEMA IF NOT EXISTS `manage server`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `manage server`;

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
    service_name ENUM('GAMES', 'FILES', 'FORUM', 'ADMIN', 'BACKEND') NOT NULL,
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

CREATE TABLE IF NOT EXISTS storage_region (
    storage_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    volume VARCHAR(2) NOT NULL,
    region_root VARCHAR(64) NOT NULL,
    filepath VARCHAR(192) NOT NULL,

    user_path VARCHAR(260)
        GENERATED ALWAYS AS (
            CONCAT(volume, ':\\', region_root, '\\', filepath)
        ) STORED,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_storage_enabled (enabled),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS admin_credentials (
    admin_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    admin_password_hash VARCHAR(255),

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS superadmin_credentials (
    superadmin_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    superadmin_password_hash VARCHAR(255),

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT IGNORE INTO admin_credentials (user_id)
SELECT id FROM users
WHERE role IN ('ADMIN', 'SUPERADMIN');

INSERT IGNORE INTO superadmin_credentials (user_id)
SELECT id FROM users
WHERE role = 'SUPERADMIN';

DROP TRIGGER IF EXISTS users_after_insert_privilege_credentials;
DROP TRIGGER IF EXISTS users_after_update_privilege_credentials;
DROP TRIGGER IF EXISTS admin_credentials_before_insert_role_check;
DROP TRIGGER IF EXISTS superadmin_credentials_before_insert_role_check;

DELIMITER //

CREATE TRIGGER users_after_insert_privilege_credentials
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    IF NEW.role IN ('ADMIN', 'SUPERADMIN') THEN
        INSERT IGNORE INTO admin_credentials (user_id)
        VALUES (NEW.id);
    END IF;

    IF NEW.role = 'SUPERADMIN' THEN
        INSERT IGNORE INTO superadmin_credentials (user_id)
        VALUES (NEW.id);
    END IF;
END//

CREATE TRIGGER users_after_update_privilege_credentials
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    IF NEW.role IN ('ADMIN', 'SUPERADMIN') THEN
        INSERT IGNORE INTO admin_credentials (user_id)
        VALUES (NEW.id);
    ELSE
        DELETE FROM admin_credentials
        WHERE user_id = NEW.id;
    END IF;

    IF NEW.role = 'SUPERADMIN' THEN
        INSERT IGNORE INTO superadmin_credentials (user_id)
        VALUES (NEW.id);
    ELSE
        DELETE FROM superadmin_credentials
        WHERE user_id = NEW.id;
    END IF;
END//

CREATE TRIGGER admin_credentials_before_insert_role_check
BEFORE INSERT ON admin_credentials
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM users
        WHERE id = NEW.user_id
        AND role IN ('ADMIN', 'SUPERADMIN')
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'admin_credentials requires ADMIN or SUPERADMIN role';
    END IF;
END//

CREATE TRIGGER superadmin_credentials_before_insert_role_check
BEFORE INSERT ON superadmin_credentials
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM users
        WHERE id = NEW.user_id
        AND role = 'SUPERADMIN'
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'superadmin_credentials requires SUPERADMIN role';
    END IF;
END//

DELIMITER ;

CREATE USER IF NOT EXISTS 'Master_Shake'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'tormageddon monstrum rex';

GRANT SELECT
ON `manage server`.users
TO 'Master_Shake'@'localhost';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.portal_sessions
TO 'Master_Shake'@'localhost';

GRANT SELECT, INSERT
ON `manage server`.session_registry
TO 'Master_Shake'@'localhost';

GRANT SELECT, INSERT, DELETE
ON `manage server`.service
TO 'Master_Shake'@'localhost';

GRANT SELECT, INSERT
ON `manage server`.activity_log
TO 'Master_Shake'@'localhost';

CREATE USER IF NOT EXISTS 'Kairos'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'power overwhelming breathe deep';

GRANT SELECT
ON `manage server`.users
TO 'Kairos'@'localhost';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.portal_sessions
TO 'Kairos'@'localhost';

GRANT SELECT, INSERT
ON `manage server`.session_registry
TO 'Kairos'@'localhost';

GRANT SELECT, INSERT, DELETE
ON `manage server`.service
TO 'Kairos'@'localhost';

GRANT SELECT, INSERT
ON `manage server`.activity_log
TO 'Kairos'@'localhost';

CREATE USER IF NOT EXISTS 'Bifrost'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'thor was a terrible fucking movie';

GRANT SELECT
ON `manage server`.storage_region
TO 'Bifrost'@'localhost';

GRANT SELECT
ON `manage server`.portal_sessions
TO 'Bifrost'@'localhost';

GRANT SELECT
ON `manage server`.service
TO 'Bifrost'@'localhost';

GRANT SELECT
ON `manage server`.users
TO 'Bifrost'@'localhost';

CREATE USER IF NOT EXISTS 'RegionArchitect'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'hate my life right now';

GRANT SELECT
ON `manage server`.users
TO 'RegionArchitect'@'localhost';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.storage_region
TO 'RegionArchitect'@'localhost';

CREATE USER IF NOT EXISTS 'Imperator'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'magnus did absolutely everything wrong';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.users
TO 'Imperator'@'localhost';

GRANT SELECT
ON `manage server`.portal_sessions
TO 'Imperator'@'localhost';

GRANT SELECT, DELETE
ON `manage server`.service
TO 'Imperator'@'localhost';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.admin_credentials
TO 'Imperator'@'localhost';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.superadmin_credentials
TO 'Imperator'@'localhost';

GRANT INSERT
ON `manage server`.activity_log
TO 'Imperator'@'localhost';

FLUSH PRIVILEGES;