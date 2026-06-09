USE `manage server`;

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
SELECT id
FROM users
WHERE role IN ('ADMIN', 'SUPERADMIN');

INSERT IGNORE INTO superadmin_credentials (user_id)
SELECT id
FROM users
WHERE role = 'SUPERADMIN';

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