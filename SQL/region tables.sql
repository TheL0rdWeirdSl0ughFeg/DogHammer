CREATE SCHEMA IF NOT EXISTS `manage server`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `manage server`;

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