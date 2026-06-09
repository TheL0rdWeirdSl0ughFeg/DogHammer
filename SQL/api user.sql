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

FLUSH PRIVILEGES;