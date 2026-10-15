"""Exercise real audio and WebGL against Vite running on port 5173."""

import asyncio
import io
import math
import struct
import wave
from pathlib import Path

from playwright.async_api import Route, async_playwright, expect


HARNESS = """
import React from '/node_modules/.vite/deps/react.js';
import MusicPlayer from '/src/components/AudioPlayer.tsx';
import SidebarVisualizer from '/src/visualizer/SidebarVisualizer.tsx';
export default function App() {
    const [name, setName] = React.useState(undefined);
    const [playback, setPlayback] = React.useState(null);
    return React.createElement(React.Fragment, null,
        React.createElement('button', {onClick: () => setName('Test tone')}, 'Start track'),
        React.createElement('button', {onClick: () => setName('Second tone')}, 'Change track'),
        React.createElement('aside', {style: {width: 248, height: 350, display: 'flex'}},
            React.createElement(SidebarVisualizer, {playback, title: name})),
        React.createElement(MusicPlayer, {entry: name ? {content_name: name} : undefined, onPlaybackReady: setPlayback}));
}
"""


def test_audio() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * 220 * index / 8000)))
            for index in range(8000 * 45)
        ))
    return buffer.getvalue()


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, channel="msedge",
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        page = await browser.new_page(viewport={"width": 1366, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.route("**/src/App.tsx*", lambda route: route.fulfill(
            content_type="application/javascript", body=HARNESS,
        ))
        audio_bytes = test_audio()
        async def serve_audio(route: Route) -> None:
            requested = route.request.headers.get("range")
            headers = {"Accept-Ranges": "bytes"}
            start, end = 0, len(audio_bytes) - 1
            if requested:
                first, last = requested.removeprefix("bytes=").split("-")
                start = int(first)
                if last:
                    end = int(last)
                headers["Content-Range"] = f"bytes {start}-{end}/{len(audio_bytes)}"
            await route.fulfill(status=206 if requested else 200, headers=headers,
                                content_type="audio/wav", body=audio_bytes[start:end + 1])

        await page.route("**/audio/*", serve_audio)
        await page.goto("http://127.0.0.1:5173")
        preview = page.get_by_role("region", name="Live music preview")
        await expect(preview.get_by_role("button", name="Expand visualizer")).to_be_disabled()
        await page.get_by_role("button", name="Start track").click()
        await page.wait_for_function("document.querySelector('audio')?.readyState === 4")
        await expect(preview.locator("canvas")).to_be_visible()
        first_frame = await preview.locator("canvas").screenshot()
        await page.wait_for_timeout(300)
        assert first_frame != await preview.locator("canvas").screenshot(), "Preview should animate without opening a dialog"
        await preview.get_by_role("button", name="Fullscreen visualizer", exact=True).click()
        dialog = page.get_by_role("dialog", name="Music visualizer")
        await expect(dialog).to_be_visible()
        await page.wait_for_function("document.fullscreenElement !== null")
        await dialog.get_by_role("button", name="Exit fullscreen", exact=True).click()
        await expect(preview.locator("canvas")).to_have_count(0)
        await expect(dialog.get_by_role("button", name="Pause", exact=True)).to_be_visible()
        await page.wait_for_timeout(300)
        energy = await page.evaluate("""async () => {
            const {getAudioAnalysis} = await import('/src/visualizer/audio.ts');
            const graph = getAudioAnalysis(document.querySelector('audio'));
            window.originalGraph = graph;
            const bins = new Uint8Array(graph.analyser.frequencyBinCount);
            graph.analyser.getByteFrequencyData(bins);
            return Math.max(...bins);
        }""")
        assert energy > 0, "Visualizer must receive actual audio samples"
        output = Path("dist/visualizer-checks")
        output.mkdir(parents=True, exist_ok=True)
        for preset in ("halo", "terrain", "orbit"):
            await dialog.get_by_label("Scene", exact=True).select_option(preset)
            await page.wait_for_timeout(250)
            await expect(dialog.get_by_role("alert")).to_have_count(0)
            await dialog.screenshot(path=str(output / f"{preset}.png"))
        await dialog.get_by_label("Quality", exact=True).select_option("high")
        await dialog.get_by_role("button", name="Pause", exact=True).click()
        assert await page.locator("audio").evaluate("audio => audio.paused")
        seek = dialog.get_by_role("slider", name="Seek", exact=True)
        await seek.press("Home")
        for _ in range(10):
            await seek.press("ArrowRight")
        await page.wait_for_function("Math.abs(document.querySelector('audio').currentTime - 1) < 0.05")
        volume = dialog.get_by_role("slider", name="Volume", exact=True)
        await volume.press("Home")
        for _ in range(40):
            await volume.press("ArrowRight")
        assert await page.locator("audio").evaluate("audio => audio.volume") == 0.4
        await dialog.get_by_role("button", name="Mute", exact=True).click()
        assert await page.locator("audio").evaluate("audio => audio.muted")
        await dialog.get_by_role("button", name="Loop", exact=True).click()
        assert await page.locator("audio").evaluate("audio => audio.loop")
        await dialog.get_by_role("button", name="Hide controls", exact=False).click()
        await expect(dialog.get_by_role("slider", name="Seek")).to_have_count(0)
        await page.keyboard.press("h")
        await expect(dialog.get_by_role("slider", name="Seek")).to_be_visible()
        await dialog.get_by_role("button", name="Fullscreen", exact=True).click()
        await page.wait_for_function("document.fullscreenElement !== null")
        await dialog.get_by_role("button", name="Exit fullscreen", exact=True).click()
        await page.wait_for_function("document.fullscreenElement === null")
        await dialog.get_by_role("button", name="Play", exact=True).click()
        await dialog.get_by_role("button", name="Close visualizer").click()
        await expect(dialog).to_have_count(0)
        await expect(preview.locator("canvas")).to_be_visible()
        await expect(preview.locator("canvas")).to_have_attribute("aria-label", "Particle orbit music visualization")
        await preview.screenshot(path=str(output / "sidebar.png"))
        assert not await page.locator("audio").evaluate("audio => audio.paused")
        await page.get_by_role("button", name="Change track").click()
        await page.wait_for_function("document.querySelector('audio').src.includes('Second')")
        for _ in range(3):
            await page.get_by_role("button", name="Expand visualizer", exact=True).click()
            await expect(dialog).to_be_visible()
            assert await page.evaluate("""async () => {
                const {getAudioAnalysis} = await import('/src/visualizer/audio.ts');
                return getAudioAnalysis(document.querySelector('audio')) === window.originalGraph;
            }""")
            await page.keyboard.press("Escape")
            await expect(dialog).to_have_count(0)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.get_by_role("button", name="Expand visualizer", exact=True).click()
        await expect(dialog.get_by_role("button", name="Pause", exact=True)).to_be_visible()
        await dialog.screenshot(path=str(output / "mobile.png"))
        assert await dialog.evaluate("element => element.scrollWidth <= element.clientWidth")
        library_page = await browser.new_page(viewport={"width": 2048, "height": 1157})
        library_page.on("pageerror", lambda error: errors.append(str(error)))
        await library_page.route("**/audio/*", serve_audio)
        await library_page.route("**/library?*", lambda route: route.fulfill(json={
            "jobs": [{"id": "preview-test", "content_name": "Preview test track",
                      "url": "https://example.com/music", "status": "finished",
                      "content_type": "AUDIO", "platform": "YOUTUBE"}],
            "total": 1, "next_offset": None,
        }))
        await library_page.goto("http://127.0.0.1:5173")
        await library_page.get_by_role("heading", name="Preview test track", exact=True).click()
        live_preview = library_page.get_by_role("region", name="Live music preview")
        await expect(live_preview.locator("canvas")).to_be_visible()
        preview_bounds = await live_preview.bounding_box()
        sync_bounds = await library_page.get_by_role("button", name="Sync to device", exact=True).bounding_box()
        assert preview_bounds and sync_bounds
        assert preview_bounds["x"] < 280
        assert preview_bounds["y"] + preview_bounds["height"] <= sync_bounds["y"]
        assert sync_bounds["y"] + sync_bounds["height"] <= 1157
        await expect(library_page.get_by_role("button", name="Visualizer", exact=True)).to_have_count(0)
        await library_page.screenshot(path=str(output / "library-sidebar.png"))
        await library_page.close()
        await page.add_init_script("""
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                return type.startsWith('webgl') ? null : getContext.call(this, type, ...args);
            };
        """)
        await page.reload()
        await page.get_by_role("button", name="Start track").click()
        await page.get_by_role("button", name="Expand visualizer", exact=True).click()
        await expect(dialog.get_by_role("alert")).to_contain_text("3D rendering is unavailable")
        await dialog.get_by_role("button", name="Pause", exact=True).click()
        assert await page.locator("audio").evaluate("audio => audio.paused")
        assert not errors, errors
        await browser.close()
        print("Visualizer checks passed: audio analysis, all scenes, playback, seek, volume, loop, fullscreen, reopen, track change, and mobile.")


if __name__ == "__main__":
    asyncio.run(main())
