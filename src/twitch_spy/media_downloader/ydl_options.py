"""Shared runtime and logging configuration for yt-dlp."""

import shutil
import sys
from pathlib import Path
from typing import Any

from twitch_spy import config
from twitch_spy.system_logger import logger


def downloader_options() -> dict[str, Any]:
    options: dict[str, Any] = {"logger": logger, "noprogress": True}
    bundle = getattr(sys, "_MEIPASS", None)
    node_name = "node.exe" if sys.platform == "win32" else "node"
    bundled_node = Path(bundle) / "node-runtime" / node_name if bundle else None
    node = (
        str(bundled_node)
        if bundled_node is not None and bundled_node.is_file()
        else shutil.which("node")
    )
    options["js_runtimes"] = {"deno": {}}
    if node:
        options["js_runtimes"]["node"] = {"path": node}
    if config.FFMPEG_LOCATION:
        options["ffmpeg_location"] = config.FFMPEG_LOCATION
    return options
