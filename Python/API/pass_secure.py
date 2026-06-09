from passlib.hash import bcrypt

bcrypt = bcrypt.using(rounds=12)

MAX_BCRYPT_LENGTH = 72

def hash_pass(password: str) -> str:
    password = password[:MAX_BCRYPT_LENGTH]
    return bcrypt.hash(password)

def verify_pass(password: str, record: str) -> bool:
    password = password[:MAX_BCRYPT_LENGTH]
    return bcrypt.verify(password, record)

if __name__ == "__main__":
    password = input("Password: ")

    hashed = hash_pass(password)

    print()
    print("Generated bcrypt hash:")
    print(hashed)