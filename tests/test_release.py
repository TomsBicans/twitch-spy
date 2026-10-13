from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

from scripts import release


@pytest.mark.parametrize(("tags", "initial", "bump", "expected"), [
    ([], "0.1.0", "patch", "0.1.0"),
    (["v0.1.9", "v0.1.641", "v0.1.99"], "0.1.0", "patch", "0.1.642"),
    (["v0.1.641", "v0.2.0"], "0.1.0", "patch", "0.2.1"),
    (["v0.1.641"], "0.1.0", "minor", "0.2.0"),
    (["v0.1.641"], "0.1.0", "major", "1.0.0"),
    (["v0.1.2", "v9.0.0-rc.1", "other", "v01.2.3"], "0.1.0", "patch", "0.1.3"),
])
def test_next_version(tags: list[str], initial: str, bump: str, expected: str) -> None:
    assert release.next_version(tags, initial, bump) == expected


@pytest.mark.parametrize("version", ["v0.1.1", "0.1", "01.2.3", "0.1.1\n", "1.2.-1"])
def test_invalid_version(version: str) -> None:
    with pytest.raises(ValueError):
        release.parse_version(version)


def reservation(tag: str = "v0.1.642", *, draft: bool = True) -> dict[str, Any]:
    return {
        "id": 42, "tag_name": tag, "target_commitish": "abc123",
        "draft": draft, "prerelease": False,
    }


def test_reservations_count_toward_next_version() -> None:
    tag, existing = release.select_release(
        [reservation()], ["v0.1.641"], [], "def456", "0.1.0", "patch",
    )
    assert (tag, existing) == ("v0.1.643", None)


@pytest.mark.parametrize("draft", [True, False])
def test_retry_reuses_same_commit_even_after_newer_releases(draft: bool) -> None:
    existing = reservation(draft=draft)
    tag, selected = release.select_release(
        [existing], ["v0.1.999"], [], "abc123", "0.1.0", "major",
    )
    assert tag == "v0.1.642"
    assert selected is existing


def test_existing_tag_without_release_can_be_resumed() -> None:
    assert release.select_release(
        [], ["v0.1.1"], ["v0.1.1"], "abc123", "0.1.0", "patch",
    ) == ("v0.1.1", None)


def test_ambiguous_release_fails() -> None:
    with pytest.raises(ValueError, match="Multiple releases"):
        release.select_release(
            [reservation(), reservation("v0.1.643")], [], [], "abc123", "0.1.0", "patch",
        )


def project(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "twitch-spy"\nversion = "0.1.0"\n'
        '\n[build-system]\nrequires = ["uv_build"]\n', encoding="utf-8",
    )
    (root / "uv.lock").write_text(
        'version = 1\nrevision = 3\n\n[[package]]\nname = "dependency"\n'
        'version = "0.1.0"\nsource = { registry = "https://example.com" }\n'
        '\n[[package]]\nname = "twitch-spy"\nversion = "0.1.0"\n'
        'source = { editable = "." }\n', encoding="utf-8",
    )


def test_stamp_updates_only_root_version_and_is_idempotent(tmp_path: Path) -> None:
    project(tmp_path)
    release.stamp(tmp_path, "0.1.642")
    first = [(tmp_path / name).read_bytes() for name in ("pyproject.toml", "uv.lock")]
    release.stamp(tmp_path, "0.1.642")
    assert first == [(tmp_path / name).read_bytes() for name in ("pyproject.toml", "uv.lock")]
    metadata = tomllib.loads(first[0].decode())
    lock = tomllib.loads(first[1].decode())
    assert metadata["project"]["version"] == "0.1.642"
    assert lock["version"] == 1
    assert [package["version"] for package in lock["package"]] == ["0.1.0", "0.1.642"]


def test_invalid_lock_does_not_partially_stamp_project(tmp_path: Path) -> None:
    project(tmp_path)
    original = (tmp_path / "pyproject.toml").read_bytes()
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="editable root package"):
        release.stamp(tmp_path, "0.1.642")
    assert (tmp_path / "pyproject.toml").read_bytes() == original


def assets(root: Path) -> None:
    for suffix in ("windows-x64.exe", "linux-x86_64.AppImage"):
        name = f"twitch-spy-v0.1.642-{suffix}"
        (root / name).write_bytes(b"artifact")
        digest = hashlib.sha256(b"artifact").hexdigest()
        (root / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="ascii")


def test_assets_require_both_platforms_and_matching_checksums(tmp_path: Path) -> None:
    assets(tmp_path)
    assert len(release.checked_assets(tmp_path, "0.1.642")) == 4
    (tmp_path / "twitch-spy-v0.1.642-windows-x64.exe").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="Invalid checksum"):
        release.checked_assets(tmp_path, "0.1.642")


def test_published_release_is_not_modified(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release, "api", lambda _endpoint: reservation(draft=False))
    monkeypatch.setattr(release, "command", lambda *_args, **_kwargs: pytest.fail("Unexpected write"))
    release.publish("owner/repo", "42", "0.1.642", "abc123", tmp_path)


def test_publish_rejects_wrong_commit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release, "api", lambda _endpoint: reservation())
    with pytest.raises(ValueError, match="does not match"):
        release.publish("owner/repo", "42", "0.1.642", "wrong", tmp_path)


def test_publish_uploads_before_publishing_and_does_not_promote_old_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    assets(tmp_path)
    monkeypatch.setattr(release, "api", lambda _endpoint: reservation())
    monkeypatch.setattr(release, "git_tags", lambda: [])
    monkeypatch.setattr(release, "all_releases", lambda _repo: [reservation("v0.1.643", draft=False)])
    calls: list[tuple[list[str], Any]] = []

    def fake_command(args: list[str], *, payload: Any = None) -> str:
        calls.append((args, payload))
        return ""

    monkeypatch.setattr(release, "command", fake_command)
    release.publish("owner/repo", "42", "0.1.642", "abc123", tmp_path)
    assert calls[0][0][:3] == ["gh", "release", "upload"]
    assert calls[1][1] == {"draft": False, "make_latest": "false"}


def test_upload_failure_keeps_release_draft(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets(tmp_path)
    monkeypatch.setattr(release, "api", lambda _endpoint: reservation())
    monkeypatch.setattr(release, "git_tags", lambda: [])

    def fail_upload(args: list[str]) -> str:
        assert args[:3] == ["gh", "release", "upload"]
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(release, "command", fail_upload)
    with pytest.raises(subprocess.CalledProcessError):
        release.publish("owner/repo", "42", "0.1.642", "abc123", tmp_path)


def test_all_release_pages_are_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release, "command", lambda _args: json.dumps([[reservation()], [reservation("v1.0.0")]]))
    assert len(release.all_releases("owner/repo")) == 2


def test_release_writes_are_disabled_outside_main_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/feature")
    assert release.main(["reserve"]) == 1


def test_reserve_creates_draft_for_exact_sha(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project(tmp_path)
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "git_tags", lambda: ["v0.1.641"])
    monkeypatch.setattr(release, "all_releases", lambda _repo: [])
    monkeypatch.setattr(release, "command", lambda args: "abc123" if args[1] == "rev-parse" else "")

    def create(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert endpoint == "repos/owner/repo/releases"
        assert payload["target_commitish"] == "abc123"
        assert payload["tag_name"] == "v0.1.642"
        assert payload["draft"] is True
        return {**payload, "id": 42}

    monkeypatch.setattr(release, "api", create)
    assert release.reserve("owner/repo", "abc123", "patch") == {
        "version": "0.1.642", "tag": "v0.1.642", "release_id": "42", "published": "false",
    }


def test_stamped_repository_lock_remains_valid_offline(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required to validate its lockfile")
    for name in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copy2(release.ROOT / name, tmp_path / name)
    release.stamp(tmp_path, "0.1.641")
    result = subprocess.run(
        [uv, "lock", "--check", "--offline", "--directory", str(tmp_path),
         "--cache-dir", str(tmp_path / "cache")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
