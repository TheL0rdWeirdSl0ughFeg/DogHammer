import os
import mysql.connector


REQUIRED_ENV_VARS = [
    "DB_HOST",
    "DB_REGION_USER",
    "DB_REGION_PASSWORD",
    "DB_API_NAME"
]


def check_environment():
    missing = []

    for variable in REQUIRED_ENV_VARS:
        if variable not in os.environ:
            missing.append(variable)

    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
        )


def get():
    check_environment()

    connection = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_REGION_USER"],
        password=os.environ["DB_REGION_PASSWORD"],
        database=os.environ["DB_API_NAME"]
    )

    return connection