from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen


PLATFORM_TOOLS_ARCHIVES = {
    "linux": (
        "https://dl.google.com/android/repository/platform-tools_r37.0.0-linux.zip",
        "198ae156ab285fa555987219af237b31102fefe8b9d2bc274708a8d4f2865a07",
    ),
    "windows": (
        "https://dl.google.com/android/repository/platform-tools_r37.0.0-win.zip",
        "4fe305812db074cea32903a489d061eb4454cbc90a49e8fea677f4b7af764918",
    ),
}
APPIMAGETOOL_URL = (
    "https://api.github.com/repos/AppImage/appimagetool/releases/assets/324406882"
)
APPIMAGETOOL_SHA256 = "a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0"
APPIMAGE_RUNTIME_URL = (
    "https://api.github.com/repos/AppImage/type2-runtime/releases/assets/369052327"
)
APPIMAGE_RUNTIME_SHA256 = "a2419dce47568395ae79c01ffa9a5a341dd339581352ff104d073527543177e5"
STAGING_FILES = (
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "twitch-spy.spec",
)
STAGING_DIRECTORIES = ("src", "client", "packaging", "scripts")
STAGING_IGNORES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "node_modules",
}


class BuildError(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def project_version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def is_wsl() -> bool:
    if sys.platform != "linux":
        return False
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def native_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    raise BuildError(f"Unsupported build host: {sys.platform}")


def artifact_path(root: Path, target: str) -> Path:
    version = project_version(root)
    if target == "windows":
        return root / "dist" / f"twitch-spy-v{version}-windows-x64.exe"
    if target == "linux":
        return root / "dist" / f"twitch-spy-v{version}-linux-x86_64.AppImage"
    raise BuildError(f"Unknown target: {target}")


def command_name(name: str) -> str:
    if sys.platform == "win32" and name == "npm":
        return "npm.cmd"
    return name


def require_command(name: str) -> str:
    executable = command_name(name)
    found = shutil.which(executable)
    if not found:
        raise BuildError(
            f"Required command {executable!r} was not found on PATH. "
            "Install it for the native build platform and retry."
        )
    return found


def run(
    args: list[str | Path],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> None:
    rendered = [str(arg) for arg in args]
    print(f"+ {' '.join(rendered)}", flush=True)
    subprocess.run(rendered, cwd=cwd, env=env, timeout=timeout, check=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, sha256: str | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {url}", flush=True)
    request = Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "twitch-spy-build",
        },
    )
    with urllib.request.urlopen(request) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    if sha256 and file_sha256(temporary) != sha256:
        temporary.unlink(missing_ok=True)
        raise BuildError(f"SHA-256 mismatch for {url}; review the pinned build dependency")
    temporary.replace(destination)


def ensure_platform_tools(root: Path, target: str) -> Path:
    build_dir = root / "build"
    tools_dir = build_dir / "platform-tools"
    adb_name = "adb.exe" if target == "windows" else "adb"
    adb = tools_dir / adb_name
    url, sha256 = PLATFORM_TOOLS_ARCHIVES[target]
    marker = tools_dir / ".twitch-spy-sha256"
    if adb.exists() and marker.is_file() and marker.read_text(encoding="ascii").strip() == sha256:
        return adb

    archive = build_dir / f"platform-tools-{target}.zip"
    download(url, archive, sha256=sha256)
    shutil.rmtree(tools_dir, ignore_errors=True)
    with zipfile.ZipFile(archive) as package:
        package.extractall(build_dir)
    if not adb.exists():
        raise BuildError(f"Platform-tools archive did not contain {adb_name}")
    if target == "linux":
        adb.chmod(adb.stat().st_mode | 0o111)
    marker.write_text(f"{sha256}\n", encoding="ascii")
    return adb


def prepare_build_environment(root: Path) -> None:
    require_command("uv")
    require_command("npm")
    (root / "build").mkdir(parents=True, exist_ok=True)
    (root / "dist").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(root / "build" / "uv-cache"))
    run([require_command("npm"), "ci"], cwd=root / "client", env=env)
    run([require_command("npm"), "run", "build"], cwd=root / "client", env=env)
    run([require_command("uv"), "sync", "--group", "dev"], cwd=root, env=env)


def run_pyinstaller(root: Path) -> None:
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(root / "build" / "uv-cache"))
    run(
        [require_command("uv"), "run", "pyinstaller", "--noconfirm", "--clean", "twitch-spy.spec"],
        cwd=root,
        env=env,
    )


def build_native_windows(root: Path) -> Path:
    if native_platform() != "windows":
        raise BuildError("Windows artifacts must be built by native Windows Python")
    ensure_platform_tools(root, "windows")
    prepare_build_environment(root)
    run_pyinstaller(root)
    source = root / "dist" / "twitch-spy.exe"
    destination = artifact_path(root, "windows")
    if not source.exists():
        raise BuildError(f"PyInstaller did not produce {source}")
    destination.unlink(missing_ok=True)
    source.replace(destination)
    print(f"Built {destination}")
    return destination


def ensure_pinned_file(path: Path, url: str, sha256: str) -> Path:
    if not path.exists() or file_sha256(path) != sha256:
        path.unlink(missing_ok=True)
        download(url, path, sha256=sha256)
    return path


def ensure_appimagetool(root: Path) -> Path:
    tool = ensure_pinned_file(
        root / "build" / "appimagetool-x86_64.AppImage",
        APPIMAGETOOL_URL,
        APPIMAGETOOL_SHA256,
    )
    tool.chmod(tool.stat().st_mode | 0o111)
    return tool


def ensure_appimage_runtime(root: Path) -> Path:
    return ensure_pinned_file(
        root / "build" / "runtime-x86_64",
        APPIMAGE_RUNTIME_URL,
        APPIMAGE_RUNTIME_SHA256,
    )


def build_native_linux(root: Path) -> Path:
    if native_platform() != "linux":
        raise BuildError("Linux AppImages must be built by native Linux Python")
    ensure_platform_tools(root, "linux")
    prepare_build_environment(root)
    run_pyinstaller(root)

    app_dir = root / "build" / "TwitchSpy.AppDir"
    shutil.rmtree(app_dir, ignore_errors=True)
    binary_dir = app_dir / "usr" / "bin"
    binary_dir.mkdir(parents=True)
    shutil.copytree(root / "dist" / "twitch-spy", binary_dir, dirs_exist_ok=True)
    shutil.copy2(root / "packaging" / "linux" / "AppRun", app_dir / "AppRun")
    shutil.copy2(
        root / "packaging" / "linux" / "twitch-spy.desktop",
        app_dir / "twitch-spy.desktop",
    )
    shutil.copy2(
        root / "packaging" / "assets" / "twitch-spy.png",
        app_dir / "twitch-spy.png",
    )
    (app_dir / "AppRun").chmod((app_dir / "AppRun").stat().st_mode | 0o111)

    destination = artifact_path(root, "linux")
    tool = ensure_appimagetool(root)
    runtime = ensure_appimage_runtime(root)
    env = os.environ.copy()
    env.update({"ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"})
    run([tool, "--runtime-file", runtime, app_dir, destination], cwd=root, env=env)
    print(f"Built {destination}")
    return destination


def staging_ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in STAGING_IGNORES or name.endswith(".pyc")}


def copy_staging_source(root: Path, staging: Path) -> None:
    for relative in STAGING_FILES:
        source = root / relative
        if not source.exists():
            raise BuildError(f"Required staging input is missing: {relative}")
        shutil.copy2(source, staging / relative)
    for relative in STAGING_DIRECTORIES:
        source = root / relative
        shutil.copytree(source, staging / relative, ignore=staging_ignore)


def capture(args: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def windows_temp_directory(root: Path) -> Path:
    require_command("cmd.exe")
    require_command("wslpath")
    command_cwd = Path("/mnt/c") if Path("/mnt/c").is_dir() else root
    output = capture(["cmd.exe", "/d", "/c", "echo", "%TEMP%"], cwd=command_cwd)
    windows_paths = [line.strip() for line in output.splitlines() if re.match(r"^[A-Za-z]:[\\/]", line.strip())]
    if not windows_paths:
        raise BuildError(f"Could not determine Windows TEMP from cmd.exe output: {output!r}")
    windows_temp = windows_paths[-1]
    linux_temp = capture(["wslpath", "-u", windows_temp], cwd=root)
    directory = Path(linux_temp)
    if not directory.is_dir():
        raise BuildError(f"Windows temporary directory is unavailable from WSL: {directory}")
    return directory


def to_windows_path(path: Path, root: Path) -> str:
    return capture([require_command("wslpath"), "-w", str(path)], cwd=root)


def delegate_windows_build(root: Path, keep_staging: bool = False) -> Path:
    if not is_wsl():
        raise BuildError(
            "Cross-platform Windows delegation is supported only from WSL. "
            "Run this command with native Windows Python instead."
        )
    launcher = shutil.which("py.exe")
    if not launcher:
        raise BuildError("Windows Python launcher py.exe was not found from WSL")

    staging = Path(tempfile.mkdtemp(prefix="twitch-spy-build-", dir=windows_temp_directory(root)))
    print(f"Staging Windows build in {staging}")
    try:
        copy_staging_source(root, staging)
        windows_script = to_windows_path(staging / "scripts" / "build.py", root)
        run(
            [launcher, "-3.13", windows_script, "build", "--target", "windows", "--native-only"],
            cwd=staging,
        )
        staged_artifact = artifact_path(staging, "windows")
        if not staged_artifact.exists():
            raise BuildError(f"Delegated build did not produce {staged_artifact}")
        destination = artifact_path(root, "windows")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_artifact, destination)
        print(f"Copied Windows artifact to {destination}")
        return destination
    finally:
        if keep_staging:
            print(f"Retained Windows staging directory: {staging}")
        else:
            shutil.rmtree(staging, ignore_errors=True)


def delegate_windows_smoke(root: Path, artifact: Path, port: int | None = None) -> None:
    if not is_wsl():
        raise BuildError("Windows smoke delegation is supported only from WSL")
    launcher = shutil.which("py.exe")
    if not launcher:
        raise BuildError("Windows Python launcher py.exe was not found from WSL")

    staging = Path(tempfile.mkdtemp(prefix="twitch-spy-smoke-", dir=windows_temp_directory(root)))
    try:
        (staging / "scripts").mkdir()
        (staging / "dist").mkdir()
        shutil.copy2(root / "scripts" / "build.py", staging / "scripts" / "build.py")
        shutil.copy2(root / "pyproject.toml", staging / "pyproject.toml")
        shutil.copy2(artifact, staging / "dist" / artifact.name)
        windows_script = to_windows_path(staging / "scripts" / "build.py", root)
        args = [launcher, "-3.13", windows_script, "smoke", "--target", "windows"]
        if port is not None:
            args.extend(["--port", str(port)])
        run(args, cwd=staging)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def build_target(root: Path, target: str, keep_staging: bool, native_only: bool) -> list[Path]:
    if target == "all":
        if native_platform() == "windows":
            raise BuildError("A native Windows host cannot build the Linux AppImage; use CI or Linux")
        return [
            build_native_linux(root),
            delegate_windows_build(root, keep_staging=keep_staging),
        ]
    if target == "linux":
        return [build_native_linux(root)]
    if target == "windows":
        if native_platform() == "windows":
            return [build_native_windows(root)]
        if native_only:
            raise BuildError("--native-only forbids WSL delegation")
        return [delegate_windows_build(root, keep_staging=keep_staging)]
    raise BuildError(f"Unknown target: {target}")


def verify(root: Path, tag: str | None = None) -> None:
    if tag:
        expected = f"v{project_version(root)}"
        if tag != expected:
            raise BuildError(f"Tag {tag!r} does not match project version {expected!r}")
    prepare_build_environment(root)
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(root / "build" / "uv-cache"))
    run([require_command("uv"), "run", "pytest", "-v"], cwd=root, env=env)
    run([require_command("npm"), "run", "lint"], cwd=root / "client", env=env)


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def seed_smoke_library(data_dir: Path) -> None:
    storage = (
        data_dir
        / "stream_downloads"
        / "audio_library"
        / "smoke-library"
        / "storage"
    )
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "local_storage.txt").write_text(
        "https://www.youtube.com/watch?v=smoke,Smoke track,None,None\n",
        encoding="utf-8",
    )


def smoke_artifact(artifact: Path, port: int | None = None) -> None:
    artifact = artifact.resolve()
    if not artifact.exists():
        raise BuildError(f"Artifact does not exist: {artifact}")
    port = port or available_port()
    windows_from_wsl = artifact.suffix.lower() == ".exe" and is_wsl()
    data_parent = windows_temp_directory(repository_root()) if windows_from_wsl else None
    data_dir = Path(tempfile.mkdtemp(prefix="twitch-spy-smoke-", dir=data_parent))
    seed_smoke_library(data_dir)
    output_dir = to_windows_path(data_dir, repository_root()) if windows_from_wsl else str(data_dir)
    env = os.environ.copy()
    if artifact.suffix == ".AppImage":
        env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    run([artifact, "--check-tools"], cwd=artifact.parent, env=env, timeout=15)
    process = subprocess.Popen(
        [str(artifact), "--no-browser", "--port", str(port), "--output-dir", output_dir],
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(150):
            try:
                with urlopen(f"{base}/health", timeout=1) as response:
                    health = json.load(response)
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise BuildError("Packaged application did not become ready")
        if health.get("status") != "ok":
            raise BuildError(f"Unexpected health response: {health}")
        html = urlopen(base, timeout=2).read().decode()
        if '<div id="root"></div>' not in html:
            raise BuildError("Packaged frontend root was not served")
        asset = re.search(r'(?:src|href)="(/assets/[^"]+)"', html)
        if not asset or urlopen(f"{base}{asset.group(1)}", timeout=2).status != 200:
            raise BuildError("Packaged frontend asset was not served")
        handshake = urlopen(f"{base}/socket.io/?EIO=4&transport=polling", timeout=2).read()
        if not handshake.startswith(b"0"):
            raise BuildError("Socket.IO handshake failed")
        token = html.split('name="twitch-spy-shutdown-token" content="', 1)[1].split('"', 1)[0]
        request = Request(
            f"{base}/shutdown",
            method="POST",
            headers={"X-Twitch-Spy-Shutdown": token},
        )
        urlopen(request, timeout=2).read()
        process.wait(timeout=10)
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def selected_artifacts(root: Path, target: str) -> list[Path]:
    targets = ("linux", "windows") if target == "all" else (target,)
    artifacts = [artifact_path(root, item) for item in targets]
    existing = [artifact for artifact in artifacts if artifact.exists()]
    if not existing:
        raise BuildError(f"No {target} desktop artifacts found in {root / 'dist'}")
    return existing


def write_checksums(artifacts: list[Path]) -> None:
    for artifact in artifacts:
        digest = file_sha256(artifact)
        checksum = artifact.with_name(artifact.name + ".sha256")
        checksum.write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
        print(checksum)


def list_artifacts(root: Path) -> None:
    dist = root / "dist"
    if not dist.exists():
        return
    for path in sorted(dist.iterdir()):
        if path.is_file() and (
            path.suffix in {".AppImage", ".exe", ".sha256"}
            or path.name.endswith(".AppImage.sha256")
        ):
            print(path.name)


def clean(root: Path) -> None:
    for path in (root / "build", root / "dist", root / "client" / "dist"):
        shutil.rmtree(path, ignore_errors=True)
        print(f"Removed {path}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build and verify Twitch Spy desktop releases")
    subcommands = result.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build", help="Build a desktop artifact")
    build.add_argument("--target", choices=("linux", "windows", "all"), default=None)
    build.add_argument("--keep-staging", action="store_true")
    build.add_argument("--native-only", action="store_true", help=argparse.SUPPRESS)

    verify_command = subcommands.add_parser("verify", help="Run project verification")
    verify_command.add_argument("--tag")

    smoke = subcommands.add_parser("smoke", help="Smoke-test packaged artifacts")
    smoke.add_argument("--target", choices=("linux", "windows", "all"), default="all")
    smoke.add_argument("--port", type=int, default=None)

    checksums = subcommands.add_parser("checksums", help="Generate artifact checksums")
    checksums.add_argument("--target", choices=("linux", "windows", "all"), default="all")

    subcommands.add_parser("artifacts", help="List generated artifacts")
    subcommands.add_parser("clean", help="Remove generated build output")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = repository_root()
    try:
        if args.command == "build":
            target = args.target or native_platform()
            build_target(root, target, args.keep_staging, args.native_only)
        elif args.command == "verify":
            verify(root, tag=args.tag)
        elif args.command == "smoke":
            for artifact in selected_artifacts(root, args.target):
                if artifact.suffix.lower() == ".exe" and is_wsl():
                    delegate_windows_smoke(root, artifact, port=args.port)
                else:
                    smoke_artifact(artifact, port=args.port)
        elif args.command == "checksums":
            write_checksums(selected_artifacts(root, args.target))
        elif args.command == "artifacts":
            list_artifacts(root)
        elif args.command == "clean":
            clean(root)
        return 0
    except (BuildError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
