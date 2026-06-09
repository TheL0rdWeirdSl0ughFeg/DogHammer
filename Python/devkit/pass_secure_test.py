from passlib.hash import bcrypt

MAX_BCRYPT_LENGTH = 72

def hash_pass(password: str) -> str:
    password = password[:MAX_BCRYPT_LENGTH]
    return bcrypt.hash(password)

def verify_pass(password: str, record: str) -> bool:
    password = password[:MAX_BCRYPT_LENGTH]
    return bcrypt.verify(password, record)

if __name__ == "__main__":
    test_pass = "testing testing 123"
    
    hashed = hash_pass(test_pass)
    print("Hashed pass:", hashed)
    
    result = verify_pass(test_pass, hashed)
    print("Verified:", result)