"""Run with Vite on port 5173 using uv run --with playwright python."""

import asyncio
import io
import re
import wave
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from playwright.async_api import Route, async_playwright, expect

from check_library_browser import track


async def main() -> None:
    songs = [{**track(i), "content_name": f"Pool {i:04d}"} for i in range(51)]
    songs.extend([
        {**track(51), "content_name": "Other song"},
        {**track(52), "content_name": "Pool failed", "status": "failed"},
    ])
    audio = io.BytesIO()
    with wave.open(audio, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 8000 * 60)
    audio_bytes = audio.getvalue()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page(viewport={"width": 1366, "height": 768})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.add_init_script("""
            window.mediaHandlers = {};
            const session = navigator.mediaSession;
            const setActionHandler = session.setActionHandler.bind(session);
            session.setActionHandler = (action, handler) => {
                setActionHandler(action, handler);
                window.mediaHandlers[action] = handler;
            };
        """)

        async def library(route: Route) -> None:
            offset = int(parse_qs(urlparse(route.request.url).query)["offset"][0])
            end = min(offset + 48, len(songs))
            await route.fulfill(json={
                "jobs": songs[offset:end], "total": len(songs),
                "next_offset": end if end < len(songs) else None,
            })

        await page.route("**/library?*", library)
        await page.route("**/jobs/*/thumbnail", lambda route: route.fulfill(status=204))

        async def serve_audio(route: Route) -> None:
            headers = {"Accept-Ranges": "bytes"}
            requested = route.request.headers.get("range")
            if requested:
                first, last = requested.removeprefix("bytes=").split("-")
                start = int(first)
                end = min(int(last), len(audio_bytes) - 1) if last else len(audio_bytes) - 1
                headers["Content-Range"] = f"bytes {start}-{end}/{len(audio_bytes)}"
                await route.fulfill(status=206, headers=headers, content_type="audio/wav",
                                    body=audio_bytes[start:end + 1])
            else:
                await route.fulfill(headers=headers, content_type="audio/wav", body=audio_bytes)

        await page.route("**/audio/*", serve_audio)
        await page.goto("http://127.0.0.1:5173")
        await expect(page).to_have_title("twitch-spy")
        await page.keyboard.press("Space")
        await expect(page).to_have_title("twitch-spy")
        assert await page.locator("audio").evaluate("audio => audio.paused")
        await expect(page.get_by_text("52 matching songs", exact=True)).to_be_visible()
        search = page.get_by_role("textbox", name="Search tracks")
        await search.fill("Pool")
        await expect(page.get_by_text("51 matching songs", exact=True)).to_be_visible()
        await page.get_by_role("heading", name="Pool 0000", exact=True).click()
        player = page.locator("audio")

        async def source(name: str) -> None:
            await expect(player).to_have_attribute("src", re.compile(r"/audio/" + re.escape(name) + "$"))

        async def finish_song() -> None:
            await page.wait_for_function("""() => {
                const audio = document.querySelector('audio');
                return !audio.paused && audio.readyState >= 2 && Number.isFinite(audio.duration);
            }""")
            await player.evaluate("audio => { audio.currentTime = audio.duration - 0.15; }")

        await source("Pool%200000")
        await page.evaluate("window.mediaHandlers.previoustrack({action: 'previoustrack'})")
        await source("Pool%200050")
        await page.evaluate("window.mediaHandlers.nexttrack({action: 'nexttrack'})")
        await source("Pool%200000")
        await page.evaluate("window.mediaHandlers.nexttrack({action: 'nexttrack'})")
        await source("Pool%200001")
        await page.evaluate("window.mediaHandlers.previoustrack({action: 'previoustrack'})")
        await source("Pool%200000")
        await expect(page.get_by_role("button", name="Pause", exact=True)).to_be_enabled()
        await page.wait_for_function("!document.querySelector('audio').paused && document.querySelector('audio').currentTime > 0")
        await expect(page).to_have_title("Pool 0000")
        await page.evaluate("document.activeElement.blur()")
        scroll_position = await page.evaluate("window.scrollY")
        await page.keyboard.down("Space")
        await expect(page).to_have_title("twitch-spy")
        assert await player.evaluate("audio => audio.paused")
        await page.keyboard.down("Space")
        await page.keyboard.up("Space")
        assert await player.evaluate("audio => audio.paused")
        assert await page.evaluate("window.scrollY") == scroll_position
        await page.keyboard.press("Space")
        await expect(page).to_have_title("Pool 0000")
        for shortcut in ("Control+Space", "Alt+Space", "Shift+Space", "Meta+Space"):
            await page.keyboard.press(shortcut)
            assert not await player.evaluate("audio => audio.paused")
        await search.focus()
        await page.keyboard.press("Space")
        await expect(search).to_have_value("Pool ")
        assert not await player.evaluate("audio => audio.paused")
        await search.fill("Pool")
        urls = page.locator("textarea")
        await urls.focus()
        await page.keyboard.press("Space")
        await expect(urls).to_have_value(" ")
        assert not await player.evaluate("audio => audio.paused")
        await urls.fill("")
        await page.locator("#statusFilter").focus()
        await page.keyboard.press("Space")
        assert not await player.evaluate("audio => audio.paused")
        await page.keyboard.press("Escape")
        await page.get_by_role("button", name="Pause", exact=True).focus()
        await page.keyboard.press("Space")
        await expect(page).to_have_title("twitch-spy")
        await page.keyboard.press("Space")
        await expect(page).to_have_title("Pool 0000")
        await page.locator(".rhap_container").focus()
        await page.keyboard.press("Space")
        await expect(page).to_have_title("twitch-spy")
        await page.keyboard.press("Space")
        await expect(page).to_have_title("Pool 0000")
        await page.get_by_role("button", name="Pause", exact=True).click()
        await expect(page).to_have_title("twitch-spy")
        await page.get_by_role("button", name="Play", exact=True).click()
        await expect(page).to_have_title("Pool 0000")
        await page.get_by_role("button", name="Previous song", exact=True).click()
        await source("Pool%200050")
        await expect(page).to_have_title("Pool 0050")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Pool%200000")
        await player.evaluate("audio => audio.dispatchEvent(new Event('ended'))")
        await source("Pool%200000")
        await expect(page).to_have_title("twitch-spy")
        await page.get_by_role("button", name="Autoplay", exact=True).click()
        await player.evaluate("audio => audio.dispatchEvent(new Event('ended'))")
        await source("Pool%200001")
        await expect(page).to_have_title("Pool 0001")

        await search.fill("Pool 000")
        await page.get_by_role("button", name="Shuffle", exact=True).click()
        await expect(page.get_by_role("button", name="Previous song")).to_be_disabled()
        assert await page.evaluate("window.mediaHandlers.previoustrack === null")
        seen = {await player.get_attribute("src")}
        for _ in range(9):
            await page.get_by_role("button", name="Next song", exact=True).click()
            current = await player.get_attribute("src")
            await expect(page).to_have_title(unquote(urlparse(current or "").path.removeprefix("/audio/")))
            assert current not in seen, current
            seen.add(current)
        last = await player.get_attribute("src")
        await finish_song()
        await expect(player).to_have_js_property("ended", True)
        await expect(player).to_have_attribute("src", last or "")
        await page.evaluate("window.mediaHandlers.previoustrack({action: 'previoustrack'})")
        await expect(player).not_to_have_attribute("src", last or "")
        await page.evaluate("window.mediaHandlers.nexttrack({action: 'nexttrack'})")
        await expect(player).to_have_attribute("src", last or "")

        await search.fill("Other")
        await expect(player).to_have_attribute("src", last or "")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Other%20song")
        await expect(page.get_by_role("button", name="Next song")).to_be_disabled()
        assert await page.evaluate("window.mediaHandlers.nexttrack === null")
        await search.fill("no matches")
        await expect(page.get_by_role("button", name="Next song")).to_be_disabled()
        await expect(page.get_by_role("button", name="Previous song")).to_be_disabled()
        assert await page.evaluate("window.mediaHandlers.nexttrack === null && window.mediaHandlers.previoustrack === null")
        await search.fill("Pool")
        await page.locator("#statusFilter").select_option("all")
        await expect(page.get_by_text("51 matching songs", exact=True)).to_be_visible()
        await page.get_by_role("button", name="Show more tracks").click()
        await page.get_by_role("heading", name="Pool failed", exact=True).click()
        await source("Other%20song")

        await page.get_by_role("button", name="Shuffle", exact=True).click()
        await page.get_by_role("button", name="Previous song", exact=True).click()
        await source("Pool%200050")
        params = parse_qs(urlparse(page.url).query)
        assert params["position"] == ["-1"]
        assert params["from"] == ["-1"]
        await page.get_by_role("button", name="Previous song", exact=True).click()
        await source("Pool%200049")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Pool%200050")
        await page.reload()
        await source("Pool%200050")
        await expect(search).to_have_value("Pool")
        await expect(page.get_by_role("button", name="Previous song")).to_be_enabled()
        await page.get_by_role("button", name="Show playback queue").click()
        await expect(page.locator('#queue-tracks [aria-current="true"]')).to_contain_text(
            "Pool 0050",
        )
        await page.get_by_role("button", name="Previous song", exact=True).click()
        await source("Pool%200049")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Pool%200050")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Other%20song")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Pool%200000")
        await page.get_by_role("button", name="Close playback queue").click()

        await page.goto("http://127.0.0.1:5173/?q=Pool%20000&autoplay=1&repeat=invalid")
        repeat_off = page.get_by_role("button", name="Repeat off", exact=True)
        repeat_queue = page.get_by_role("button", name="Repeat queue", exact=True)
        repeat_track = page.get_by_role("button", name="Repeat track", exact=True)
        autoplay = page.get_by_role("button", name="Autoplay", exact=True)
        await expect(repeat_off).to_be_visible()
        assert "repeat" not in parse_qs(urlparse(page.url).query)
        await page.get_by_role("heading", name="Pool 0008", exact=True).click()
        await expect(page.get_by_role("button", name="Next song")).to_be_enabled()
        await finish_song()
        await source("Pool%200009")
        await page.get_by_role("button", name="Show playback queue").click()
        await expect(page.get_by_text("Nothing up next", exact=True)).to_be_visible()
        await finish_song()
        await expect(page.get_by_role("button", name="Play", exact=True)).to_be_enabled()
        await source("Pool%200009")
        assert await player.evaluate("audio => audio.ended")
        await page.get_by_role("button", name="Close playback queue").click()

        await autoplay.click()
        await repeat_off.click()
        await expect(autoplay).to_have_attribute("aria-pressed", "true")
        await page.get_by_role("button", name="Play", exact=True).click()
        await finish_song()
        await source("Pool%200000")
        await page.reload()
        await expect(repeat_queue).to_be_visible()
        await source("Pool%200000")
        if await player.evaluate("audio => audio.paused"):
            await page.get_by_role("button", name="Play", exact=True).click()
        await repeat_queue.click()
        await expect(repeat_track).to_be_visible()
        assert await player.evaluate("audio => audio.loop")
        await finish_song()
        await page.wait_for_function("""() => {
            const audio = document.querySelector('audio');
            return !audio.paused && audio.currentTime > 0 && audio.currentTime < 1;
        }""")
        await source("Pool%200000")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await source("Pool%200001")
        assert await player.evaluate("audio => audio.loop")

        await page.get_by_role("button", name="Expand visualizer", exact=True).click()
        visualizer = page.get_by_role("dialog", name="Music visualizer")
        await visualizer.get_by_role("button", name="Repeat track", exact=True).click()
        await visualizer.get_by_role("button", name="Close visualizer").click()
        await expect(repeat_off).to_be_visible()
        await expect(autoplay).to_have_attribute("aria-pressed", "false")
        assert not await player.evaluate("audio => audio.loop")
        await search.fill("Pool 0001")
        await repeat_off.click()
        assert await player.evaluate("audio => audio.loop")
        await autoplay.click()
        await expect(repeat_off).to_be_visible()
        assert not await player.evaluate("audio => audio.loop")

        await search.fill("Pool 0010")
        await page.get_by_role("heading", name="Pool 0010", exact=True).click()
        await search.fill("Pool 000")
        await page.get_by_role("button", name="Previous song", exact=True).click()
        await source("Pool%200009")
        await repeat_off.click()
        await finish_song()
        await source("Pool%200000")
        await autoplay.click()

        await page.set_viewport_size({"width": 390, "height": 844})
        await expect(page.get_by_role("button", name="Next song")).to_be_visible()
        await expect(page.get_by_role("button", name="Shuffle", exact=True)).to_be_visible()
        for name in ("Next song", "Previous song", "Autoplay", "Shuffle", "Repeat off"):
            bounds = await page.get_by_role("button", name=name, exact=True).bounding_box()
            assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390
        Path("dist").mkdir(exist_ok=True)
        await page.screenshot(path="dist/music-controls-mobile.png")
        assert not errors, errors
        await browser.close()
        print(
            "Passed: Space playback shortcut and focus guards, sequence, full "
            "search pool, autoplay, shuffle cycle/history, query changes, "
            "filtered-out anchor navigation and bookmark restore, empty/single "
            "pools, failed tracks, three repeat modes and mobile layout"
        )


if __name__ == "__main__":
    asyncio.run(main())
