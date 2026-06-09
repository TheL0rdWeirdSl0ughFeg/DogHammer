USE `manage server`;

CREATE USER IF NOT EXISTS 'RegionArchitect'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'hate my life right now';

GRANT SELECT
ON `manage server`.users
TO 'RegionArchitect'@'localhost';

GRANT SELECT, INSERT, UPDATE
ON `manage server`.storage_region
TO 'RegionArchitect'@'localhost';

FLUSH PRIVILEGES;