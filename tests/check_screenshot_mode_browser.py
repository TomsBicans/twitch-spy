"""Verify screenshot masking and capture the README previews with synthetic data."""

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.async_api import Page, async_playwright, expect

from check_library_browser import track
from check_playback_queue_browser import mock_library


async def assert_masked(page: Page) -> None:
    visible = await page.locator("body").inner_text()
    attributes = await page.locator("[title], [alt], [aria-label], input, textarea").evaluate_all(
        """elements => elements.map(element => [element.title, element.alt,
            element.getAttribute('aria-label'), element.value]).flat().join(' ')""",
    )
    for text in (visible, attributes, page.url, await page.title()):
        assert "PRIVATE" not in text, text
        assert "SECRET" not in text, text
    sources = await page.locator("img").evaluate_all(
        "images => images.map(image => image.getAttribute('src'))",
    )
    assert all(source.startswith("data:image/svg+xml") for source in sources)
    backgrounds = await page.locator('[class*="thumbnail"], [class*="backdrop"]').evaluate_all(
        "elements => elements.map(element => getComputedStyle(element).backgroundImage)",
    )
    assert backgrounds and all(
        source == "none" or "data:image/svg+xml" in source for source in backgrounds
    ), backgrounds
    assert urlparse(page.url).query == "screenshot=1"


async def set_screenshot_mode(page: Page, enabled: bool) -> None:
    await expect(page.get_by_role("button", name="Screenshot mode", exact=True)).to_have_count(0)
    await page.get_by_role("button", name="Health and logs").click()
    panel = page.get_by_role("region", name="Health and resource usage")
    if enabled:
        await expect(panel.get_by_text(
            "PRIVATE log containing a SECRET source URL", exact=True,
        )).to_be_visible()
    await expect(panel.get_by_role("button", name="Screenshot mode", exact=True)).not_to_be_visible()
    await panel.get_by_text("Developer tools", exact=True).click()
    toggle = panel.get_by_role("button", name="Screenshot mode", exact=True)
    await toggle.click()
    await expect(toggle).to_have_attribute("aria-pressed", str(enabled).lower())
    if enabled:
        await expect(panel.get_by_text(
            "Diagnostics and logs are hidden while Screenshot mode is enabled.",
        )).to_be_visible()
        await expect(panel.locator("pre, table")).to_have_count(0)
        await assert_masked(page)
    await panel.get_by_role("button", name="Close", exact=True).click()
    await expect(panel).to_have_count(0)


async def main() -> None:
    songs = [
        {**track(index), "content_name": f"PRIVATE song {index:03d}",
         "url": f"https://youtube.com/watch?v=SECRET_SOURCE_{index}"}
        for index in range(65)
    ]
    songs.append({**track(65), "content_name": "PRIVATE failed song", "status": "failed",
                  "url": "https://youtube.com/watch?v=SECRET_FAILED",
                  "error_message": "PRIVATE download failed at C:/SECRET/music"})
    songs[1]["thumbnail_image_in_base64"] = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+a9V8AAAAASUVORK5CYII="
    )
    errors: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="msedge")
        context = await browser.new_context(viewport={"width": 2048, "height": 1152})
        await mock_library(context, songs)
        page = await context.new_page()
        await page.route("**/diagnostics", lambda route: route.fulfill(json={
            "status": "running", "version": "PRIVATE build", "pid": 100,
            "uptime_seconds": 60, "cpu_percent": 1, "memory_bytes": 100_000,
            "threads": 1, "downloads_active": False, "sync_active": False,
            "tray_active": True, "browser_clients": 1,
            "processes": [{"name": "SECRET process", "pid": 100,
                           "cpu_percent": 1, "memory_bytes": 100_000, "threads": 1}],
            "logs": "PRIVATE log containing a SECRET source URL",
        }))
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:5173")
        await expect(page.get_by_text("65 matching songs", exact=True)).to_be_visible()
        search = page.get_by_role("textbox", name="Search tracks")
        await search.fill("PRIVATE")
        await page.locator("textarea").fill("https://youtube.com/watch?v=SECRET_INPUT")
        await page.get_by_role("heading", name="PRIVATE song 000", exact=True).click()
        await page.get_by_role("button", name="Autoplay", exact=True).click()
        await page.get_by_role("button", name="Shuffle", exact=True).click()
        for _ in range(3):
            await page.get_by_role("button", name="Next song", exact=True).click()
        await page.get_by_role("button", name="Show playback queue").click()
        audio = page.locator("audio")
        await page.wait_for_function("""() => {
            const audio = document.querySelector('audio');
            return !audio.paused && audio.readyState >= 2 && audio.currentTime > 0;
        }""")
        await audio.evaluate("audio => { audio.dataset.original = 'true'; audio.currentTime = 5; }")
        await page.wait_for_function("document.querySelector('audio').currentTime >= 5")
        source = await audio.get_attribute("src")
        params = parse_qs(urlparse(page.url).query)
        await set_screenshot_mode(page, True)
        await assert_masked(page)
        await expect(search).to_have_value("")
        await expect(search).to_be_disabled()
        await expect(page.locator("textarea")).to_have_value("")
        await expect(page.get_by_role("button", name="Health and logs")).to_be_enabled()
        await expect(page.get_by_role("button", name="Sync to device")).to_be_disabled()
        await expect(audio).to_have_attribute("src", source or "")
        assert await audio.evaluate("audio => audio.dataset.original === 'true' && audio.currentTime >= 5")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await assert_masked(page)
        await page.get_by_role("button", name="Previous song", exact=True).click()
        await expect(audio).to_have_attribute("src", source or "")
        await assert_masked(page)
        Path("docs").mkdir(exist_ok=True)
        await page.screenshot(path="docs/library-preview.png", animations="disabled")
        await page.get_by_role("button", name="Expand artwork", exact=True).click()
        view = page.get_by_role("region", name="Expanded artwork")
        await expect(view.get_by_role("img")).to_be_visible()
        await assert_masked(page)
        title = await view.get_by_role("heading").inner_text()
        await expect(page.locator('#queue-tracks [aria-current="true"]')).to_contain_text(title)
        await page.screenshot(path="docs/artwork-preview.png", animations="disabled")
        await page.get_by_role("button", name="Expand visualizer", exact=True).click()
        await expect(page.get_by_role("dialog", name="Music visualizer")).to_be_visible()
        await assert_masked(page)
        await page.get_by_role("button", name="Close visualizer").click()
        await set_screenshot_mode(page, False)
        await expect(page.locator('#queue-tracks [aria-current="true"]')).to_contain_text("PRIVATE")
        await expect(search).to_have_value("PRIVATE")
        await expect(page.locator("textarea")).to_have_value(
            "https://youtube.com/watch?v=SECRET_INPUT",
        )
        restored = parse_qs(urlparse(page.url).query)
        for key in ("track", "anchor", "position", "shuffle", "autoplay", "seed", "q"):
            assert restored[key] == params[key], (key, restored, params)
        await page.locator("#statusFilter").select_option("all")
        await page.get_by_role("button", name="Show more tracks").click()
        await set_screenshot_mode(page, True)
        await page.get_by_text("Error details", exact=True).click()
        await assert_masked(page)
        await set_screenshot_mode(page, False)
        await expect(page.get_by_text("PRIVATE download failed", exact=False)).to_be_visible()
        await page.get_by_role("button", name="Close playback queue").click()
        await page.set_viewport_size({"width": 390, "height": 844})
        await set_screenshot_mode(page, True)
        await assert_masked(page)
        await expect(page.get_by_role("button", name="Health and logs")).to_be_visible()
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        # Direct screenshot links must never request the original artwork.
        fresh = await browser.new_context()
        await mock_library(fresh, songs)
        fresh_page = await fresh.new_page()
        requests: list[str] = []
        fresh_page.on("pageerror", lambda error: errors.append(str(error)))
        fresh_page.on("request", lambda request: requests.append(request.url))
        query = urlencode({"screenshot": "1", "track": songs[1]["url"],
                           "anchor": songs[1]["url"], "q": "PRIVATE"})
        await fresh_page.goto(f"http://127.0.0.1:5173/?{query}")
        await expect(fresh_page.get_by_text("65 matching songs", exact=True)).to_be_visible()
        await assert_masked(fresh_page)
        assert not any("/thumbnail" in url for url in requests), requests
        await fresh_page.reload()
        await expect(fresh_page.get_by_text("65 matching songs", exact=True)).to_be_visible()
        await assert_masked(fresh_page)
        assert not errors, errors
        await browser.close()
    print("Passed: masked artwork/text/URLs/errors, queue and visualizer, playback continuity, "
          "restoration, mobile layout, direct links and reload, no original artwork requests")


if __name__ == "__main__":
    asyncio.run(main())
