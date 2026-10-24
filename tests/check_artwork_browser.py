"""Exercise expanded artwork against Vite running on port 5173."""

import asyncio
import re
from pathlib import Path

from playwright.async_api import Route, async_playwright, expect

from check_library_browser import track
from check_visualizer_browser import test_audio


async def main() -> None:
    songs = [track(index) for index in range(60)]
    songs[3].pop("thumbnail_url")
    songs[4]["thumbnail_image_in_base64"] = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+a9V8AAAAASUVORK5CYII="
    )
    audio = test_audio()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.route("**/library?*", lambda route: route.fulfill(json={
            "jobs": songs, "total": len(songs), "next_offset": None,
        }))

        async def thumbnail(route: Route) -> None:
            index = int(route.request.url.split("/jobs/")[1].split("/")[0])
            if index == 2:
                await route.fulfill(status=404)
                return
            width, height = (600, 900) if index == 1 else (1600, 900)
            await route.fulfill(content_type="image/svg+xml", body=f"""
                <svg xmlns="http://www.w3.org/2000/svg"
                    width="{width}" height="{height}">
                    <defs><linearGradient id="g" x2="1" y2="1">
                        <stop stop-color="#ff9666"/>
                        <stop offset="1" stop-color="#5632a8"/>
                    </linearGradient></defs>
                    <rect width="100%" height="100%" fill="url(#g)"/>
                    <circle cx="50%" cy="40%" r="150" fill="#ffe2b3"/>
                    <text x="50%" y="75%" text-anchor="middle"
                        fill="white" font-size="48">Track {index:04d}</text>
                </svg>
            """)

        await page.route("**/jobs/*/thumbnail", thumbnail)
        await page.route("**/audio/*", lambda route: route.fulfill(
            content_type="audio/wav", body=audio,
        ))
        await page.goto("http://127.0.0.1:5173")
        expand = page.get_by_role("button", name="Expand artwork", exact=True)
        await expect(expand).to_be_disabled()
        search = page.get_by_role("textbox", name="Search tracks")
        await search.fill("Track 00")
        await page.get_by_role("heading", name="Track 0000", exact=True).click()
        await page.get_by_role("button", name="Show more tracks").click()
        await page.evaluate("window.scrollTo(0, 500)")
        scroll_position = await page.evaluate("window.scrollY")
        player = page.locator("audio")
        await page.wait_for_function("""() => {
            const audio = document.querySelector('audio');
            return !audio.paused && audio.currentTime > 1;
        }""")
        await player.evaluate("""audio => {
            audio.dataset.original = 'true';
            audio.volume = 0.4;
        }""")
        previous_time = await player.evaluate("audio => audio.currentTime")
        await expand.click()
        view = page.get_by_role("region", name="Expanded artwork")
        await expect(view).to_be_visible()
        await expect(search).not_to_be_visible()
        back = page.get_by_role("button", name="Back to library")
        collapse = page.get_by_role("button", name="Collapse artwork")
        await expect(back).to_be_focused()
        await expect(collapse).to_have_attribute("aria-expanded", "true")
        playback = await player.evaluate("""audio => ({
            original: audio.dataset.original, paused: audio.paused,
            time: audio.currentTime, volume: audio.volume,
        })""")
        assert playback["original"] == "true", playback
        assert not playback["paused"], playback
        assert playback["time"] >= previous_time, playback
        assert playback["volume"] == 0.4, playback
        await expect(view.get_by_role("img")).to_have_attribute(
            "src", re.compile(r"/jobs/0/thumbnail$"),
        )

        async def check_layout() -> None:
            artwork_bounds = await view.bounding_box()
            dock = page.locator('[class*="nowPlayingDock"]')
            dock_bounds = await dock.bounding_box()
            picture_bounds = await view.get_by_role("img").bounding_box()
            assert artwork_bounds and dock_bounds and picture_bounds
            artwork_bottom = artwork_bounds["y"] + artwork_bounds["height"]
            assert abs(artwork_bottom - dock_bounds["y"]) < 2
            assert picture_bounds["height"] > 100
            assert picture_bounds["y"] >= artwork_bounds["y"]
            assert picture_bounds["y"] + picture_bounds["height"] <= dock_bounds["y"]
            assert await view.get_by_role("img").evaluate("""image =>
                getComputedStyle(image).objectFit === 'contain'
                && image.naturalWidth > 0
            """)
            for name in ("Next song", "Previous song", "Autoplay", "Shuffle", "Pause"):
                button = page.get_by_role("button", name=name, exact=True)
                await expect(button).to_be_in_viewport()

        await check_layout()
        Path("dist").mkdir(exist_ok=True)
        await page.screenshot(path="dist/artwork-desktop.png")
        await page.get_by_role("button", name="Pause", exact=True).click()
        assert await player.evaluate("audio => audio.paused")
        await page.get_by_role("button", name="Play", exact=True).click()
        await page.get_by_role("button", name="Autoplay", exact=True).click()
        await player.evaluate("audio => audio.dispatchEvent(new Event('ended'))")
        await expect(view.get_by_role("heading")).to_have_text("Track 0001")
        await expect(view.get_by_role("img")).to_have_attribute(
            "src", re.compile(r"/jobs/1/thumbnail$"),
        )
        await check_layout()
        await page.get_by_role("button", name="Next song", exact=True).click()
        await expect(view.get_by_text("No artwork for this track")).to_be_visible()
        await expect(view.get_by_role("img")).to_have_count(0)
        await page.get_by_role("button", name="Next song", exact=True).click()
        await expect(view.get_by_role("heading")).to_have_text("Track 0003")
        await expect(view.get_by_text("No artwork for this track")).to_be_visible()
        await page.get_by_role("button", name="Next song", exact=True).click()
        await expect(view.get_by_role("img")).to_have_attribute(
            "src", "data:image/jpeg;base64," + songs[4]["thumbnail_image_in_base64"],
        )
        await expect(view.get_by_role("heading")).to_have_text("Track 0004")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await expect(view.get_by_role("img")).to_have_attribute(
            "src", re.compile(r"/jobs/5/thumbnail$"),
        )
        await page.keyboard.press("Escape")
        await expect(view).to_have_count(0)
        await expect(expand).to_be_focused()
        await expect(search).to_have_value("Track 00")
        assert await page.locator('[role="button"]').count() == 60
        assert await page.evaluate("window.scrollY") == scroll_position

        await expand.click()
        await back.click()
        await expect(view).to_have_count(0)
        await expand.click()
        await collapse.click()
        await expect(view).to_have_count(0)

        await page.set_viewport_size({"width": 390, "height": 844})
        await expand.click()
        await check_layout()
        await page.screenshot(path="dist/artwork-mobile.png")
        await page.set_viewport_size({"width": 844, "height": 390})
        await check_layout()
        await page.keyboard.press("Escape")
        await expect(view).to_have_count(0)

        await page.set_viewport_size({"width": 1440, "height": 1000})
        await expand.click()
        await page.get_by_role("button", name="Sync to device", exact=True).click()
        await expect(page.get_by_role("dialog")).to_be_visible()
        await page.keyboard.press("Escape")
        await expect(page.get_by_role("dialog")).not_to_be_visible()
        await expect(view).to_be_visible()
        await page.get_by_role("button", name="Health and logs").click()
        await expect(view).to_have_count(0)
        await expect(page.get_by_role("region", name="Health and resource usage")).to_be_visible()
        assert await player.evaluate("audio => audio.dataset.original === 'true'")
        assert not errors, errors
        await browser.close()
        print(
            "Passed: artwork follows autoplay, controls keep playing, "
            "missing/broken/embedded artwork, library state and focus restored, "
            "desktop/mobile layout, modal Escape and diagnostics navigation"
        )


if __name__ == "__main__":
    asyncio.run(main())
