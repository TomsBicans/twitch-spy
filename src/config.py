import os.path as path
import sys

PYTHON_SCRIPTS_DIR = path.dirname(__file__)
PROJECT_ROOT = path.dirname(PYTHON_SCRIPTS_DIR)
CHAT_LOGS = path.join(PROJECT_ROOT, "logs")

sys.path.extend([PROJECT_ROOT, PYTHON_SCRIPTS_DIR])
