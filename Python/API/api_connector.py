import os
import mysql.connector


REQUIRED_ENV_VARS = [
    "DB_HOST",
    "DB_API_USER",
    "DB_API_PASSWORD",
    "DB_API_NAME"
]


def check_env():
    missing = []

    for variable in REQUIRED_ENV_VARS:
        if variable not in os.environ:
            missing.append(variable)

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )


def get():
    check_env()

    connection = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_API_USER"],
        password=os.environ["DB_API_PASSWORD"],
        database=os.environ["DB_API_NAME"]
    )

    return connection