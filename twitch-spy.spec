import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / "client" / "dist"), "client/dist"), (str(root / "THIRD_PARTY_NOTICES.md"), ".")]
platform_tools = root / "build" / "platform-tools"
if platform_tools.exists():
    datas.append((str(platform_tools), "platform-tools"))
datas += collect_data_files("imageio_ffmpeg")
datas += collect_data_files("yt_dlp_ejs", includes=["**/*.js"])
datas += copy_metadata("yt-dlp-ejs")
node_dir = root / "build" / "node-runtime"
node_name = "node.exe" if sys.platform == "win32" else "node"
if not (node_dir / node_name).is_file():
    raise RuntimeError("Missing Node runtime; build with scripts/build.py")
datas.append((str(node_dir / "LICENSE"), "node-runtime"))
datas += copy_metadata("twitch-spy")
datas.append((str(root / "packaging" / "assets" / "twitch-spy.png"), "packaging/assets"))

a = Analysis(
    [str(root / "src" / "twitch_spy" / "main.py")],
    pathex=[str(root / "src")],
    binaries=[(str(node_dir / node_name), "node-runtime")],
    datas=datas,
    hiddenimports=["engineio.async_drivers.threading"] + (["pystray._win32"] if sys.platform == "win32" else []),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
icon = str(root / "packaging" / "assets" / ("twitch-spy.ico" if sys.platform == "win32" else "twitch-spy.png"))

if sys.platform == "win32":
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="twitch-spy", debug=False, bootloader_ignore_signals=False,
        strip=False, upx=True, console=False, icon=icon,
    )
else:
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True,
        name="twitch-spy", debug=False, bootloader_ignore_signals=False,
        strip=False, upx=True, console=False, icon=icon,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="twitch-spy")
