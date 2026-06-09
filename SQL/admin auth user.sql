CREATE USER IF NOT EXISTS 'Imperator'@'localhost'
IDENTIFIED WITH caching_sha2_password
BY 'magnus did absolutely everything wrong';

GRANT SELECT
ON `manage server`.portal_sessions
TO 'Imperator'@'localhost';

GRANT SELECT
ON `manage server`.service
TO 'Imperator'@'localhost';

GRANT SELECT, INSERT
ON `manage server`.users
TO 'Imperator'@'localahost';

GRANT SELECT
ON `manage server`.admin_credentials
TO 'Imperator'@'localhost';

GRANT SELECT
ON `manage server`.superadmin_credentials
TO 'Imperator'@'localhost';

GRANT INSERT
ON `manage server`.activity_log
TO 'Imperator'@'localhost';

FLUSH PRIVILEGES;