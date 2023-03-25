import re

def safe_pathname(dir: str) -> str:
    # Replace any character that is not allowed in Windows filenames with an underscore
    return re.sub(r'[\\/:*?"<>| ]', '_', dir)