CREATE USER 'Kairos'@'localhost'
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

FLUSH PRIVILEGES;