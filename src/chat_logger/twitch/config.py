import os.path as path
import sys
import yaml


def read_config(config_path: str):
    if not path.exists(config_path):
        raise Exception(f"No config found at :{config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


PYTHON_SCRIPTS_DIR = path.dirname(__file__)
PROJECT_ROOT = path.dirname(PYTHON_SCRIPTS_DIR)
CHAT_LOGS = path.join(PROJECT_ROOT, "logs")
CONFIG = read_config(path.join(PROJECT_ROOT, "config.yml"))

sys.path.extend([PROJECT_ROOT, PYTHON_SCRIPTS_DIR])
