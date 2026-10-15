"""Preview the startup UI on Windows and save a screenshot under dist/."""

import ctypes
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab

repository = Path(__file__).resolve().parents[1]
(repository / "dist").mkdir(exist_ok=True)
ctypes.windll.user32.SetProcessDPIAware()
root = tk.Tk()
root.withdraw()
root.overrideredirect(True)
frame = tk.Frame(root, name="root")
frame.pack()
canvas = tk.Canvas(frame, name="canvas", highlightthickness=0)
canvas.pack()
root.tk.eval("trace add variable status_text write [list canvas_text_update .root.canvas vartext]")
root.tk.eval((repository / "packaging/startup.tcl").read_text(encoding="utf-8"))
root.deiconify()
messages = ["Preparing bundled components...", "node-runtime/node.exe", "imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe", "Loading desktop settings...", "Locating bundled media tools...", "Loading application modules...", "Preparing the application...", "Starting the local server..."]
for index, message in enumerate(messages):
    root.after(index * 100, lambda value=message: root.setvar("status_text", value))
def capture() -> None:
    x, y = root.winfo_rootx(), root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height())).save(repository / "dist/startup-preview.png")
    root.destroy()
root.after(1800, capture)
root.mainloop()
