from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 5000


def load_config(path: str | Path = "settings.ini") -> ServerConfig:
    config = configparser.ConfigParser()
    config["SERVER"] = {"host": "127.0.0.1", "port": "5000"}

    config_path = Path(path)
    if config_path.exists():
        config.read(config_path)

    host = os.getenv("MPRIS_BRIDGE_HOST", config.get("SERVER", "host"))
    port = int(os.getenv("MPRIS_BRIDGE_PORT", config.get("SERVER", "port")))
    return ServerConfig(host=host, port=port)
