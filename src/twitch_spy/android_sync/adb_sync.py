r"""
Android one-way library sync via adb.exe (WSL-compatible).

WSL path conversion
-------------------
`adb.exe push` is a Windows binary, so it needs Windows-style paths.
We convert Linux paths with `wslpath -w`:

    $ wslpath -w /home/user/music/track.mp3
    \\wsl.localhost\Ubuntu\home\user\music\track.mp3

Remote path quoting
-------------------
`adb shell <cmd>` passes <cmd> to /bin/sh on the device.
We use `shlex.quote()` on every remote path argument, which produces
POSIX single-quoted strings:

    shlex.quote('/sdcard/My Music/track.mp3')
    → "'/sdcard/My Music/track.mp3'"

This safely handles spaces, parentheses, and most unicode in filenames.

Example usage
-------------
    syncer = AndroidLibrarySync(
        adb_exe="adb.exe",
        android_dest="/sdcard/SdCardBackup/Music",
    )

    if not syncer.device_connected():
        raise RuntimeError("No device found — run: adb.exe devices")

    plan = syncer.plan_sync("/home/user/data/stream_downloads/audio_library")
    print(f"{len(plan.files_to_transfer)} files to transfer, {plan.skipped_count} already synced")

    result = syncer.execute_plan(plan, progress_callback=lambda i, n, op, s: print(f"[{i}/{n}] {s} {op.filename}"))
    print(result)
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class FileTransferOp:
    local_path: str    # Absolute Linux path (WSL)
    remote_path: str   # Absolute Android path
    size_bytes: int
    filename: str      # Basename, for display

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SyncPlan:
    dirs_to_create: list[str]                # Remote dirs that must exist before push
    files_to_transfer: list[FileTransferOp]  # Ordered transfer operations
    skipped_count: int                       # Files already present on device
    total_transfer_bytes: int

    def to_dict(self) -> dict:
        return {
            "dirs_to_create": self.dirs_to_create,
            "files_to_transfer": [op.to_dict() for op in self.files_to_transfer],
            "skipped_count": self.skipped_count,
            "total_transfer_bytes": self.total_transfer_bytes,
        }


@dataclass
class SyncResult:
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Core class ─────────────────────────────────────────────────────────────────

class AndroidLibrarySync:
    """
    One-way sync from a local library directory to an Android device via adb.exe.

    Designed for WSL: local paths are converted to Windows paths with `wslpath -w`
    before being passed to `adb.exe push`.

    v1 behaviour:
    - Copy-only: never deletes or overwrites remote files.
    - Files that already exist at the exact remote path are skipped.
    - Directory structure relative to `local_dir` is preserved under `android_dest`.
    """

    def __init__(
        self,
        adb_exe: str = "adb.exe",
        android_dest: str = "/sdcard/SdCardBackup/Music",
    ) -> None:
        self.adb_exe = adb_exe
        self.android_dest = android_dest.rstrip("/")

    # ── Low-level subprocess helpers ──────────────────────────────────────────

    def _run(self, args: list[str], check: bool = False) -> subprocess.CompletedProcess:
        """Run a subprocess, always capturing output. Never raises by default."""
        logger.debug("run: %s", " ".join(args))
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )

    def _remote_shell(self, command: str) -> subprocess.CompletedProcess:
        """
        Run a shell command on the Android device.

        `command` is passed as a single string to `adb shell`, which hands it
        to /bin/sh on the device.  Always use shlex.quote() on any path that
        appears inside `command` so spaces and special characters are safe.

        Example:
            self._remote_shell(f"mkdir -p {shlex.quote(remote_dir)}")
        """
        return self._run([self.adb_exe, "shell", command])

    def _wsl_to_windows(self, linux_path: str) -> str:
        r"""
        Convert an absolute WSL Linux path to a Windows UNC path using wslpath.

        Example:
            /home/user/music/track.mp3
            → \\wsl.localhost\Ubuntu\home\user\music\track.mp3

        Required because adb.exe is a Windows binary and does not understand
        Linux paths directly.
        """
        result = self._run(["wslpath", "-w", linux_path], check=True)
        return result.stdout.strip()

    # ── Device ────────────────────────────────────────────────────────────────

    def list_devices(self) -> list[str]:
        """Return serial numbers of all connected (online) devices."""
        result = self._run([self.adb_exe, "devices"])
        devices = []
        for line in result.stdout.splitlines()[1:]:  # skip header
            line = line.strip()
            if "\t" in line:
                serial, state = line.split("\t", 1)
                if state.strip() == "device":
                    devices.append(serial.strip())
        return devices

    def device_connected(self) -> bool:
        """Return True if at least one device is online."""
        return len(self.list_devices()) > 0

    # ── Remote filesystem ─────────────────────────────────────────────────────

    def ensure_remote_dir(self, remote_dir: str) -> None:
        """Create `remote_dir` (and all parents) on the device if not present."""
        cmd = f"mkdir -p {shlex.quote(remote_dir)}"
        result = self._remote_shell(cmd)
        if result.returncode != 0:
            raise RuntimeError(
                f"mkdir -p failed for {remote_dir!r}: {result.stderr.strip()}"
            )
        logger.debug("remote dir ready: %s", remote_dir)

    def remote_file_exists(self, remote_path: str) -> bool:
        """Return True if `remote_path` exists on the device."""
        cmd = f"test -e {shlex.quote(remote_path)} && echo 1 || echo 0"
        result = self._remote_shell(cmd)
        return result.stdout.strip() == "1"

    def list_remote_files(self, remote_dir: str) -> set[str]:
        """
        Return a set of all file paths currently under `remote_dir` on the device.

        Uses a single `adb shell find` call — much faster than checking each
        file individually when the library is large.
        """
        cmd = f"find {shlex.quote(remote_dir)} -type f 2>/dev/null"
        result = self._remote_shell(cmd)
        if result.returncode != 0 and not result.stdout.strip():
            logger.warning(
                "find returned non-zero for %s (directory may be empty or missing)",
                remote_dir,
            )
            return set()
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}

    # ── Push ──────────────────────────────────────────────────────────────────

    def push_file(self, local_path: str, remote_path: str) -> bool:
        """
        Push a single file to the device.

        Converts the local Linux path to a Windows path via `wslpath -w` before
        calling `adb.exe push`.  Returns True on success, False on any error.
        Errors are logged but not raised, so callers can continue on failure.
        """
        try:
            win_path = self._wsl_to_windows(local_path)
        except subprocess.CalledProcessError as exc:
            logger.error("wslpath failed for %r: %s", local_path, exc)
            return False

        # remote_path is passed as a direct argument — no shell involved here,
        # so no additional quoting is needed at this layer.
        result = self._run([self.adb_exe, "push", win_path, remote_path])
        if result.returncode != 0:
            logger.error(
                "push failed [%s → %s]: %s",
                local_path,
                remote_path,
                result.stderr.strip(),
            )
            return False

        logger.info("pushed: %s → %s", local_path, remote_path)
        return True

    # ── Sync ──────────────────────────────────────────────────────────────────

    def plan_sync(self, local_dir: str) -> SyncPlan:
        """
        Walk `local_dir` and compute which files need to be transferred.

        Does NOT write anything to the device.  Only reads the remote file list
        (one bulk `adb shell find` call) and the local filesystem.

        The relative directory structure under `local_dir` is preserved under
        `android_dest`.  Example:

            local_dir  = /data/audio_library
            file       = /data/audio_library/Playlist A/track.mp3
            remote     = /sdcard/SdCardBackup/Music/Playlist A/track.mp3
        """
        local_root = Path(local_dir).resolve()
        if not local_root.is_dir():
            raise ValueError(f"local_dir does not exist or is not a directory: {local_dir}")

        logger.info("planning sync: %s → %s", local_root, self.android_dest)

        # One bulk query avoids O(n) adb round-trips.
        existing_remote = self.list_remote_files(self.android_dest)
        logger.info("device has %d existing files under %s", len(existing_remote), self.android_dest)

        dirs_to_create: list[str] = []
        files_to_transfer: list[FileTransferOp] = []
        skipped = 0
        seen_dirs: set[str] = set()

        for local_file in sorted(local_root.rglob("*")):
            if not local_file.is_file():
                continue

            rel = local_file.relative_to(local_root)
            # Build remote path by joining parts individually so that the
            # separator is always "/" regardless of the local OS.
            remote_path = self.android_dest + "/" + "/".join(rel.parts)
            remote_dir = remote_path.rsplit("/", 1)[0]

            if remote_path in existing_remote:
                skipped += 1
                logger.debug("skip (exists): %s", remote_path)
                continue

            # Track unique remote directories that need creating.
            if remote_dir != self.android_dest and remote_dir not in seen_dirs:
                dirs_to_create.append(remote_dir)
                seen_dirs.add(remote_dir)

            files_to_transfer.append(
                FileTransferOp(
                    local_path=str(local_file),
                    remote_path=remote_path,
                    size_bytes=local_file.stat().st_size,
                    filename=local_file.name,
                )
            )

        total_bytes = sum(op.size_bytes for op in files_to_transfer)
        logger.info(
            "plan ready — transfer: %d files (%.1f MB), skip: %d, new dirs: %d",
            len(files_to_transfer),
            total_bytes / 1_048_576,
            skipped,
            len(dirs_to_create),
        )
        return SyncPlan(
            dirs_to_create=dirs_to_create,
            files_to_transfer=files_to_transfer,
            skipped_count=skipped,
            total_transfer_bytes=total_bytes,
        )

    def execute_plan(
        self,
        plan: SyncPlan,
        progress_callback=None,
    ) -> SyncResult:
        """
        Execute a previously computed SyncPlan.

        `progress_callback`, if provided, is called after each file transfer:
            callback(current: int, total: int, op: FileTransferOp, status: str)
        where `status` is "ok" or "failed".

        Errors on individual files are logged and counted but do not abort
        the rest of the sync.
        """
        result = SyncResult(skipped=plan.skipped_count)
        total = len(plan.files_to_transfer)

        # Step 1: ensure all required remote directories exist.
        for remote_dir in plan.dirs_to_create:
            try:
                self.ensure_remote_dir(remote_dir)
            except RuntimeError as exc:
                # Log but continue — the push itself will fail if the dir is
                # truly missing, and that failure is captured per-file below.
                logger.warning("dir creation warning: %s", exc)

        # Step 2: push files one by one.
        for i, op in enumerate(plan.files_to_transfer, start=1):
            ok = self.push_file(op.local_path, op.remote_path)
            if ok:
                result.uploaded += 1
                status = "ok"
            else:
                result.failed += 1
                result.errors.append(op.remote_path)
                status = "failed"

            if progress_callback:
                try:
                    progress_callback(i, total, op, status)
                except Exception as exc:
                    logger.warning("progress_callback raised: %s", exc)

        logger.info(
            "sync complete — uploaded: %d  skipped: %d  failed: %d",
            result.uploaded,
            result.skipped,
            result.failed,
        )
        return result


# ── CLI entrypoint for manual testing ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Android one-way sync (dry-run by default)"
    )
    parser.add_argument("local_dir", help="Local directory to sync")
    parser.add_argument(
        "--android-dest",
        default="/sdcard/SdCardBackup/Music",
        help="Remote root on the Android device",
    )
    parser.add_argument(
        "--adb-exe",
        default="adb.exe",
        help="adb executable name (default: adb.exe for WSL)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually transfer files (default is dry-run / plan only)",
    )
    args = parser.parse_args()

    syncer = AndroidLibrarySync(adb_exe=args.adb_exe, android_dest=args.android_dest)

    print("Checking for connected devices...")
    devices = syncer.list_devices()
    if not devices:
        print("No device found.  Make sure USB debugging is on and run: adb.exe devices")
        sys.exit(1)
    print(f"Device(s): {', '.join(devices)}")

    print(f"\nBuilding sync plan: {args.local_dir} → {args.android_dest}")
    plan = syncer.plan_sync(args.local_dir)

    print(f"\n=== Sync Plan ===")
    print(f"  Files to transfer : {len(plan.files_to_transfer)}  ({plan.total_transfer_bytes / 1_048_576:.1f} MB)")
    print(f"  Files to skip     : {plan.skipped_count}  (already on device)")
    print(f"  Dirs to create    : {len(plan.dirs_to_create)}")

    if not args.execute:
        print("\nDry run.  Pass --execute to transfer files.")
        sys.exit(0)

    def on_progress(current: int, total: int, op: FileTransferOp, status: str) -> None:
        mark = "✓" if status == "ok" else "✗"
        print(f"  [{current:>4}/{total}] {mark} {op.filename}")

    print("\nStarting transfer...")
    result = syncer.execute_plan(plan, progress_callback=on_progress)

    print(f"\n=== Result ===")
    print(f"  Uploaded : {result.uploaded}")
    print(f"  Skipped  : {result.skipped}")
    print(f"  Failed   : {result.failed}")
    if result.errors:
        print("  Errors:")
        for err in result.errors:
            print(f"    - {err}")
    sys.exit(0 if result.failed == 0 else 1)
