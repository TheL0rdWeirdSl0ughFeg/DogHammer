UPDATE admin_credentials
SET admin_password_hash = '$2b$12$H2SZvqjL9E19MvdhPzMgc.v0uuTtqcLeuZpgMZSYRpS3dN5Ndp0jy'
WHERE user_id = (
    SELECT id
    FROM users
    WHERE username = 'AtlasUnchanged'
);

UPDATE superadmin_credentials
SET superadmin_password_hash = '$2b$12$wYpr7Ao4Z7pzxaCHIpt1tOHUeddhckbyErIxf.gUNZlvevJj/AQuG'
WHERE user_id = (
    SELECT id
    FROM users
    WHERE username = 'AtlasUnchanged'
);