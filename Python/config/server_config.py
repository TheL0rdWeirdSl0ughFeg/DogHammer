import json
import os


CONFIG_DIR = "config"
SERVER_CONFIG_FILE = os.path.join(CONFIG_DIR, "server_config.json")
CLIENT_CONFIG_FILE = os.path.join(CONFIG_DIR, "client_config.json")


DEFAULT_SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000
}


DEFAULT_CLIENT_CONFIG = {
    "server_url": "http://127.0.0.1:8000"
}


def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def load_json_config(path: str, default: dict) -> dict:
    ensure_config_dir()

    if not os.path.exists(path):
        save_json_config(path, default)
        return default.copy()

    with open(path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def save_json_config(path: str, data: dict) -> None:
    ensure_config_dir()

    with open(path, "w", encoding="utf-8") as config_file:
        json.dump(data, config_file, indent=4)


def load_server_config() -> dict:
    return load_json_config(SERVER_CONFIG_FILE, DEFAULT_SERVER_CONFIG)


def save_server_config(host: str, port: int) -> None:
    save_json_config(
        SERVER_CONFIG_FILE,
        {
            "host": host,
            "port": port
        }
    )


def load_client_config() -> dict:
    return load_json_config(CLIENT_CONFIG_FILE, DEFAULT_CLIENT_CONFIG)


def save_client_config(server_url: str) -> None:
    save_json_config(
        CLIENT_CONFIG_FILE,
        {
            "server_url": server_url
        }
    )