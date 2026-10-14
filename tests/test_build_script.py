from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


from scripts import build


def project(tmp_path: Path, version: str = "1.2.3") -> Path:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "twitch-spy"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_project_version_and_artifact_paths(tmp_path):
    root = project(tmp_path)

    assert build.project_version(root) == "1.2.3"
    assert build.artifact_path(root, "linux").name == "twitch-spy-v1.2.3-linux-x86_64.AppImage"
    assert build.artifact_path(root, "windows").name == "twitch-spy-v1.2.3-windows-x64.exe"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def versioned_repository(root: Path) -> None:
    project(root)
    git(root, "init", "--quiet")
    git(root, "config", "user.name", "Build tests")
    git(root, "config", "user.email", "build@example.invalid")
    git(root, "add", "pyproject.toml")
    git(root, "commit", "--quiet", "-m", "initial")
    git(root, "tag", "v1.2.3")


def test_clean_tag_build_uses_release_version(tmp_path: Path) -> None:
    versioned_repository(tmp_path)
    assert build.local_version(tmp_path) == "1.2.3"


def test_commits_after_release_have_development_version(tmp_path: Path) -> None:
    versioned_repository(tmp_path)
    git(tmp_path, "commit", "--quiet", "--allow-empty", "-m", "next")
    sha = git(tmp_path, "rev-parse", "--short=12", "HEAD")
    assert build.local_version(tmp_path) == f"1.2.4.dev1+g{sha}"


def test_uncommitted_files_never_claim_release_version(tmp_path: Path) -> None:
    versioned_repository(tmp_path)
    (tmp_path / "new.py").write_text("print('new')", encoding="utf-8")
    version = build.local_version(tmp_path)
    assert version.startswith("1.2.4.dev0+g")
    assert version.endswith(".dirty")


def test_local_build_stamps_snapshot_without_modifying_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_release import project as release_project

    release_project(tmp_path)
    before = [(tmp_path / name).read_bytes() for name in ("pyproject.toml", "uv.lock")]
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(build, "local_version", lambda _root: "0.1.1.dev2+g123abc.dirty")
    monkeypatch.setattr(build, "STAGING_FILES", ("pyproject.toml", "uv.lock"))
    monkeypatch.setattr(build, "STAGING_DIRECTORIES", ())

    def fake_build(root: Path, *_args: object, **_kwargs: object) -> list[Path]:
        assert root != tmp_path
        assert build.project_version(root) == "0.1.1.dev2+g123abc.dirty"
        artifact = build.artifact_path(root, "windows")
        artifact.parent.mkdir()
        artifact.write_bytes(b"built")
        return [artifact]

    monkeypatch.setattr(build, "build_target", fake_build)
    build.build_versioned(tmp_path, "windows", False, False, True)
    assert before == [(tmp_path / name).read_bytes() for name in ("pyproject.toml", "uv.lock")]
    assert build.selected_artifacts(tmp_path, "windows")[0].read_bytes() == b"built"
    assert not list((tmp_path / "build").glob("local-*"))


def test_ci_refuses_unstamped_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RELEASE_VERSION", "1.2.4")
    with pytest.raises(build.BuildError, match="must stamp"):
        build.build_versioned(tmp_path, "windows", False, False, True)


def test_smoke_selection_uses_last_build_even_after_source_changes(tmp_path: Path) -> None:
    project(tmp_path, "9.0.0")
    dist = tmp_path / "dist"
    dist.mkdir()
    filename = "twitch-spy-v1.2.3-windows-x64.exe"
    (dist / filename).write_bytes(b"built")
    (dist / "latest-windows.json").write_text(json.dumps({"artifact": filename}), encoding="utf-8")
    assert build.selected_artifacts(tmp_path, "windows") == [dist / filename]


def test_wsl_detection(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "release", lambda: "6.6.0-microsoft-standard-WSL2")

    assert build.is_wsl()


def test_staging_copy_uses_explicit_inputs_and_excludes_outputs(tmp_path, monkeypatch):
    root = tmp_path / "root"
    staging = tmp_path / "stage"
    root.mkdir()
    staging.mkdir()
    for name in build.STAGING_FILES:
        (root / name).write_text(name, encoding="utf-8")
    for name in build.STAGING_DIRECTORIES:
        (root / name).mkdir()
        (root / name / "kept.txt").write_text("kept", encoding="utf-8")
        (root / name / "node_modules").mkdir()
        (root / name / "node_modules" / "ignored.txt").write_text("ignored", encoding="utf-8")

    build.copy_staging_source(root, staging)

    assert (staging / "src" / "kept.txt").is_file()
    assert not (staging / "client" / "node_modules").exists()


def test_verify_rejects_mismatched_tag_before_running_commands(tmp_path):
    root = project(tmp_path)

    with pytest.raises(build.BuildError, match="does not match"):
        build.verify(root, tag="v9.9.9")


def test_write_checksums(tmp_path):
    artifact = tmp_path / "artifact.exe"
    artifact.write_bytes(b"desktop")

    build.write_checksums([artifact])

    expected = hashlib.sha256(b"desktop").hexdigest()
    assert (tmp_path / "artifact.exe.sha256").read_text(encoding="ascii") == (
        f"{expected}  artifact.exe\n"
    )


def test_platform_tools_archives_are_checksum_pinned():
    for target in ("linux", "windows"):
        url, digest = build.PLATFORM_TOOLS_ARCHIVES[target]
        assert url.startswith("https://dl.google.com/android/repository/")
        assert "platform-tools_r37.0.0" in url
        assert "latest" not in url
        assert len(digest) == 64


def test_appimage_dependencies_use_versioned_releases_and_checksums():
    assert "/releases/download/1.9.1/" in build.APPIMAGETOOL_URL
    assert build.APPIMAGETOOL_URL.endswith("/appimagetool-x86_64.AppImage")
    assert len(build.APPIMAGETOOL_SHA256) == 64
    assert "/releases/download/20251108/" in build.APPIMAGE_RUNTIME_URL
    assert build.APPIMAGE_RUNTIME_URL.endswith("/runtime-x86_64")
    assert len(build.APPIMAGE_RUNTIME_SHA256) == 64


def test_appimagetool_cache_requires_matching_digest(monkeypatch, tmp_path):
    tool = tmp_path / "build" / "appimagetool-x86_64.AppImage"
    tool.parent.mkdir()
    tool.write_bytes(b"stale")
    downloads = []

    monkeypatch.setattr(
        build,
        "file_sha256",
        lambda path: "wrong" if path == tool else build.APPIMAGETOOL_SHA256,
    )

    def fake_download(url, destination, sha256=None):
        downloads.append((url, sha256))
        destination.write_bytes(b"verified")

    monkeypatch.setattr(build, "download", fake_download)

    assert build.ensure_appimagetool(tmp_path) == tool
    assert downloads == [(build.APPIMAGETOOL_URL, build.APPIMAGETOOL_SHA256)]


def test_platform_tools_cache_requires_matching_marker(monkeypatch, tmp_path):
    tools = tmp_path / "build" / "platform-tools"
    tools.mkdir(parents=True)
    (tools / "adb").write_bytes(b"old")
    downloaded = []

    def fake_download(_url, destination, sha256=None):
        downloaded.append(sha256)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr("platform-tools/adb", b"new")

    monkeypatch.setattr(build, "download", fake_download)

    build.ensure_platform_tools(tmp_path, "linux")

    expected = build.PLATFORM_TOOLS_ARCHIVES["linux"][1]
    assert downloaded == [expected]
    assert (tools / ".twitch-spy-sha256").read_text(encoding="ascii").strip() == expected


def test_available_port_returns_bound_port(monkeypatch):
    class FakeSocket:
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def bind(self, address): assert address == ("127.0.0.1", 0)
        def getsockname(self): return ("127.0.0.1", 45123)

    monkeypatch.setattr(build.socket, "socket", lambda *_args: FakeSocket())
    assert build.available_port() == 45123


def test_smoke_library_contains_persisted_entry(tmp_path):
    build.seed_smoke_library(tmp_path)

    storage = (
        tmp_path
        / "stream_downloads"
        / "audio_library"
        / "smoke-library"
        / "storage"
        / "local_storage.txt"
    )
    assert "Smoke track" in storage.read_text(encoding="utf-8")


def test_native_windows_build_is_rejected_on_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "native_platform", lambda: "linux")

    with pytest.raises(build.BuildError, match="native Windows Python"):
        build.build_native_windows(tmp_path)


def test_windows_temp_directory_ignores_cmd_unc_warning(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "require_command", lambda name: name)
    responses = iter(
        [
            "CMD.EXE was started with a UNC path.\nC:\\Users\\test\\AppData\\Local\\Temp",
            str(tmp_path),
        ]
    )
    monkeypatch.setattr(build, "capture", lambda *_args, **_kwargs: next(responses))

    assert build.windows_temp_directory(tmp_path) == tmp_path


def test_windows_smoke_path_is_translated_from_wsl(monkeypatch, tmp_path):
    artifact = tmp_path / "app.exe"
    artifact.write_bytes(b"exe")
    windows_temp = tmp_path / "windows-temp"
    windows_temp.mkdir()
    seen = {}

    monkeypatch.setattr(build, "is_wsl", lambda: True)
    monkeypatch.setattr(build, "windows_temp_directory", lambda _root: windows_temp)
    monkeypatch.setattr(build, "to_windows_path", lambda path, _root: f"C:\\Temp\\{path.name}")
    monkeypatch.setattr(build, "run", lambda *_args, **_kwargs: None)

    class Process:
        def __init__(self, args, **_kwargs):
            seen["args"] = args
        def poll(self): return 0
        def wait(self, timeout): return 0

    monkeypatch.setattr(build.subprocess, "Popen", Process)
    monkeypatch.setattr(build, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(build.time, "sleep", lambda _seconds: None)

    with pytest.raises(build.BuildError, match="did not become ready"):
        build.smoke_artifact(artifact, port=19000)

    assert seen["args"][-1].startswith("C:\\Temp\\twitch-spy-smoke-")


def test_windows_smoke_delegation_stages_artifact(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    project(root)
    (root / "scripts").mkdir()
    (root / "scripts" / "build.py").write_text("pass", encoding="utf-8")
    artifact = root / "dist" / "twitch-spy-v1.2.3-windows-x64.exe"
    artifact.parent.mkdir()
    artifact.write_bytes(b"exe")
    windows_temp = tmp_path / "windows-temp"
    windows_temp.mkdir()
    seen = {}

    monkeypatch.setattr(build, "is_wsl", lambda: True)
    monkeypatch.setattr(build.shutil, "which", lambda name: "py.exe" if name == "py.exe" else None)
    monkeypatch.setattr(build, "windows_temp_directory", lambda _root: windows_temp)
    monkeypatch.setattr(build, "to_windows_path", lambda _path, _root: "C:\\Temp\\build.py")
    monkeypatch.setattr(build, "run", lambda args, **_kwargs: seen.setdefault("args", args))

    build.delegate_windows_smoke(root, artifact, port=19000)

    assert seen["args"][-4:] == ["--target", "windows", "--port", "19000"]
