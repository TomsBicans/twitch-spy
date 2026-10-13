from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def parse_version(value: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"Expected a numeric X.Y.Z version, got {value!r}")
    return int(match[1]), int(match[2]), int(match[3])


def release_versions(tags: list[str]) -> dict[str, tuple[int, int, int]]:
    return {
        tag: parse_version(tag[1:])
        for tag in tags
        if tag.startswith("v") and VERSION_PATTERN.fullmatch(tag[1:])
    }


def next_version(tags: list[str], initial: str, bump: str = "patch") -> str:
    versions = release_versions(tags)
    if not versions:
        parse_version(initial)
        return initial
    major, minor, patch = max(versions.values())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump != "patch":
        raise ValueError(f"Unknown bump: {bump}")
    return f"{major}.{minor}.{patch + 1}"


def command(args: list[str], *, payload: dict[str, Any] | None = None) -> str:
    result = subprocess.run(
        args, cwd=ROOT, check=True, text=True, capture_output=True,
        input=json.dumps(payload) if payload is not None else None,
    )
    return result.stdout.strip()


def api(endpoint: str, payload: dict[str, Any] | None = None) -> Any:
    args = ["gh", "api", endpoint]
    if payload is not None:
        args.extend(["--input", "-"])
    return json.loads(command(args, payload=payload))


def all_releases(repository: str) -> list[dict[str, Any]]:
    pages = json.loads(command([
        "gh", "api", f"repos/{repository}/releases?per_page=100", "--paginate", "--slurp",
    ]))
    return [release for page in pages for release in page]


def git_tags() -> list[str]:
    return command(["git", "tag", "--list"]).splitlines()


def initial_version(root: Path) -> str:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def select_release(
    releases: list[dict[str, Any]], tags: list[str], commit_tags: list[str],
    sha: str, initial: str, bump: str,
) -> tuple[str, dict[str, Any] | None]:
    matching = [
        release for release in releases
        if release_versions([release["tag_name"]])
        and (release["target_commitish"] == sha or release["tag_name"] in commit_tags)
    ]
    if len(matching) > 1:
        raise ValueError(f"Multiple releases refer to commit {sha}; resolve the ambiguity")
    if matching:
        return matching[0]["tag_name"], matching[0]
    existing = release_versions(commit_tags)
    if len(existing) > 1:
        raise ValueError(f"Multiple version tags refer to commit {sha}")
    if existing:
        return next(iter(existing)), None
    reserved = tags + [release["tag_name"] for release in releases]
    return f"v{next_version(reserved, initial, bump)}", None


def reserve(repository: str, sha: str, bump: str) -> dict[str, str]:
    if command(["git", "rev-parse", "HEAD"]) != sha:
        raise ValueError("Checkout does not match the requested source commit")
    tags = git_tags()
    commit_tags = command(["git", "tag", "--points-at", sha]).splitlines()
    tag, release = select_release(
        all_releases(repository), tags, commit_tags, sha, initial_version(ROOT), bump,
    )
    if release is None:
        release = api(f"repos/{repository}/releases", {
            "tag_name": tag, "target_commitish": sha, "name": tag,
            "draft": True, "body": f"Desktop release {tag}\n\nSource commit: `{sha}`\n",
        })
    elif release["draft"] and release["target_commitish"] != sha:
        raise ValueError("Existing draft must target the exact source SHA, not a branch")
    return {
        "version": tag[1:], "tag": tag, "release_id": str(release["id"]),
        "published": str(not release["draft"]).lower(),
    }


def replace_version(section: str, version: str) -> str:
    updated, count = re.subn(
        r'(?m)^(version\s*=\s*")[^"]+("\s*)$',
        lambda match: f"{match[1]}{version}{match[2]}", section,
    )
    if count != 1:
        raise ValueError("Expected exactly one version field in the package section")
    return updated


def stamp(root: Path, version: str) -> None:
    parse_version(version)
    project_path = root / "pyproject.toml"
    project_text = project_path.read_text(encoding="utf-8")
    project_match = re.search(r"(?ms)^\[project\]\n.*?(?=^\[|\Z)", project_text)
    if project_match is None:
        raise ValueError("Missing [project] section")
    project = tomllib.loads(project_text)["project"]
    lock_path = root / "uv.lock"
    lock_text = lock_path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)(?=^\[\[package\]\])", lock_text)
    found = 0
    for index, section in enumerate(sections):
        if not section.startswith("[[package]]"):
            continue
        package = tomllib.loads(section)["package"][0]
        if package["name"] == project["name"] and package.get("source") == {"editable": "."}:
            sections[index] = replace_version(section, version)
            found += 1
    if found != 1:
        raise ValueError("Expected exactly one editable root package in uv.lock")
    updated_project = (
        project_text[:project_match.start()]
        + replace_version(project_match[0], version)
        + project_text[project_match.end():]
    )
    # Validate both documents before changing either file.
    updated_lock = "".join(sections)
    tomllib.loads(updated_project)
    tomllib.loads(updated_lock)
    project_path.write_text(updated_project, encoding="utf-8")
    lock_path.write_text(updated_lock, encoding="utf-8")


def checked_assets(directory: Path, version: str) -> list[Path]:
    names = [
        f"twitch-spy-v{version}-windows-x64.exe",
        f"twitch-spy-v{version}-linux-x86_64.AppImage",
    ]
    assets = []
    for name in names:
        artifact = directory / name
        checksum = directory / f"{name}.sha256"
        with artifact.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if checksum.read_text(encoding="ascii").strip() != f"{digest}  {name}":
            raise ValueError(f"Invalid checksum: {checksum}")
        assets.extend([artifact, checksum])
    return assets


def publish(repository: str, release_id: str, version: str, sha: str, directory: Path) -> None:
    parse_version(version)
    endpoint = f"repos/{repository}/releases/{release_id}"
    release = api(endpoint)
    tag = f"v{version}"
    if release["tag_name"] != tag or release["target_commitish"] != sha:
        raise ValueError("Release reservation does not match the build version and commit")
    if not release["draft"]:
        print(f"{tag} is already published; leaving its artifacts unchanged")
        return
    tags = git_tags()
    if tag in tags and command(["git", "rev-list", "-n", "1", tag]) != sha:
        raise ValueError(f"Tag {tag} points to a different commit")
    assets = checked_assets(directory, version)
    command([
        "gh", "release", "upload", tag, "--repo", repository, "--clobber",
        *[str(path) for path in assets],
    ])
    published = release_versions([
        item["tag_name"] for item in all_releases(repository)
        if not item["draft"] and not item["prerelease"]
    ])
    latest = not published or parse_version(version) > max(published.values())
    command([
        "gh", "api", endpoint, "--method", "PATCH", "--input", "-",
    ], payload={"draft": False, "make_latest": str(latest).lower()})
    print(f"Published {tag} from {sha}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Allocate, stamp, and publish desktop versions")
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("next-version", help="Preview using local tags; no changes")
    preview.add_argument("--bump", choices=("patch", "minor", "major"), default="patch")
    allocation = commands.add_parser("reserve", help="Reserve a draft release (CI only)")
    allocation.add_argument("--bump", choices=("patch", "minor", "major"), default="patch")
    stamping = commands.add_parser("stamp", help="Stamp a disposable build checkout")
    stamping.add_argument("--version", required=True)
    publishing = commands.add_parser("publish", help="Publish verified draft assets (CI only)")
    publishing.add_argument("--version", required=True)
    publishing.add_argument("--release-id", required=True)
    publishing.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    args = parser.parse_args(argv)
    try:
        if args.command == "next-version":
            print(next_version(git_tags(), initial_version(ROOT), args.bump))
        elif args.command == "stamp":
            stamp(ROOT, args.version)
            print(f"Build checkout stamped with {args.version}")
        else:
            if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_REF") != "refs/heads/main":
                raise ValueError("Release writes are restricted to GitHub Actions on main")
            repository = os.environ["GITHUB_REPOSITORY"]
            sha = os.environ["GITHUB_SHA"]
            if args.command == "reserve":
                outputs = reserve(repository, sha, args.bump)
                with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
                    for key, value in outputs.items():
                        handle.write(f"{key}={value}\n")
                print(json.dumps(outputs, indent=2))
            else:
                publish(repository, args.release_id, args.version, sha, args.artifacts)
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(f"error: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
