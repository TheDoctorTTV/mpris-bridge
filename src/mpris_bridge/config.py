from __future__ import annotations

#################
### IMPORTS ###
#################

import configparser
import os
from dataclasses import dataclass
from pathlib import Path


#########################
### SERVER SETTINGS ###
#########################

@dataclass(frozen=True)
class ServerConfig:
    # Host interface the Flask server binds to.
    host: str = "127.0.0.1"
    # TCP port the Flask server listens on.
    port: int = 5000


###########################
### CONFIG LOADING ###
###########################

def load_config(path: str | Path = "settings.ini") -> ServerConfig:
    # Start with defaults so the app works without a config file.
    config = configparser.ConfigParser()
    config["SERVER"] = {"host": "127.0.0.1", "port": "5000"}

    # Read settings.ini when it exists.
    config_path = Path(path)
    if config_path.exists():
        config.read(config_path)

    # Environment variables win over the config file for service overrides.
    host = os.getenv("MPRIS_BRIDGE_HOST", config.get("SERVER", "host"))
    port = int(os.getenv("MPRIS_BRIDGE_PORT", config.get("SERVER", "port")))
    # Return an immutable settings object for the CLI.
    return ServerConfig(host=host, port=port)
