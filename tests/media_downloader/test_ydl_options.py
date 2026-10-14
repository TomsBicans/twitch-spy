from pathlib import Path

import pytest

from twitch_spy.media_downloader import ydl_options
from twitch_spy.system_logger import logger


def test_development_node_is_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(ydl_options.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(ydl_options.shutil, "which", lambda name: "/tools/node")
    options = ydl_options.downloader_options()
    assert options["js_runtimes"]["node"] == {"path": "/tools/node"}
    assert options["logger"] is logger


def test_packaged_node_does_not_require_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node = tmp_path / "node-runtime" / (
        "node.exe" if ydl_options.sys.platform == "win32" else "node"
    )
    node.parent.mkdir()
    node.touch()
    monkeypatch.setattr(ydl_options.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(ydl_options.shutil, "which", lambda name: None)
    assert ydl_options.downloader_options()["js_runtimes"]["node"] == {"path": str(node)}


def test_missing_node_preserves_deno_support(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(ydl_options.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(ydl_options.shutil, "which", lambda name: None)
    assert ydl_options.downloader_options()["js_runtimes"] == {"deno": {}}
