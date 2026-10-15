"""Compare library restoration against a Git revision using synthetic tracks."""

import argparse
from pathlib import Path
import subprocess
import tempfile
import time
import types

from twitch_spy import config

repository = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--baseline", default="HEAD", help="Git revision before the optimization")
parser.add_argument("--tracks", type=int, default=1600)
args = parser.parse_args()
if args.tracks < 1:
    parser.error("--tracks must be positive")
config.init(str(repository / "dist/benchmark-data"))
from twitch_spy.media_downloader.storage_manager import LibraryManager, StorageManager

source = subprocess.check_output(
    ["git", "show", f"{args.baseline}:src/twitch_spy/media_downloader/storage_manager.py"],
    text=True, cwd=repository,
)
previous = types.ModuleType("previous_storage")
exec(compile(source, "previous_storage.py", "exec"), previous.__dict__)
with tempfile.TemporaryDirectory(prefix="library-benchmark-") as temporary:
    root = Path(temporary)
    storage = StorageManager(temporary)
    for index in range(args.tracks):
        title = f"Benchmark Track {index:04d}"
        storage.add_entry(storage.storage_file, f"https://youtube.com/watch?v={index}", title)
        (root / f"{title}.mp3").write_bytes(b"audio")
        (root / "thumbnails" / f"{title}.jpg").write_bytes(b"artwork" * 1024)
    started = time.perf_counter()
    old = previous.LibraryManager(temporary).count_atoms()
    old_elapsed = time.perf_counter() - started
    started = time.perf_counter()
    new = list(LibraryManager(temporary).iter_atoms())
    new_elapsed = time.perf_counter() - started
    assert len(old) == len(new) == args.tracks
    print(f"{args.tracks} tracks: old {old_elapsed:.3f}s, new {new_elapsed:.3f}s; {old_elapsed/new_elapsed:.1f}x faster")
