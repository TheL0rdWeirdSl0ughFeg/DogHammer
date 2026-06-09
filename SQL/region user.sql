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

FLUSH PRIVILEGES;