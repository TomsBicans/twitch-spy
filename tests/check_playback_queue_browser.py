"""Exercise bookmarkable sequences and the queue against Vite on port 5173."""

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import BrowserContext, Page, Route, async_playwright, expect

from check_library_browser import track
from check_visualizer_browser import test_audio


async def mock_library(context: BrowserContext, songs: list[dict[str, object]]) -> None:
    async def library(route: Route) -> None:
        offset = int(parse_qs(urlparse(route.request.url).query)["offset"][0])
        if offset:
            await asyncio.sleep(0.15)
        end = min(offset + 48, len(songs))
        await route.fulfill(json={
            "jobs": songs[offset:end], "total": len(songs),
            "next_offset": end if end < len(songs) else None,
        })

    await context.route("**/library?*", library)
    await context.route("**/audio/*", lambda route: route.fulfill(
        content_type="audio/wav", body=test_audio(),
    ))
    await context.route("**/jobs/*/thumbnail", lambda route: route.fulfill(
        content_type="image/svg+xml", body="""
        <svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
          <defs><linearGradient id="g" x2="1" y2="1">
            <stop stop-color="#2a2860"/><stop offset="1" stop-color="#be736b"/>
          </linearGradient></defs>
          <rect width="1600" height="900" fill="url(#g)"/>
          <circle cx="800" cy="430" r="220" fill="#f3ceb1"/>
          <text x="800" y="770" text-anchor="middle" fill="white"
            font-size="64" font-family="sans-serif">AFTER HOURS</text>
        </svg>""",
    ))


async def queue_titles(page: Page, state: str = "upcoming") -> list[str]:
    return await page.locator(
        f'#queue-tracks [data-queue-state="{state}"] button',
    ).all_text_contents()


async def main() -> None:
    songs = [track(index) for index in range(65)]
    songs.append({**track(65), "status": "failed"})
    errors: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="msedge")
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        await mock_library(context, songs)
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:5173/?campaign=queue-test")
        await page.get_by_role("button", name="Show playback queue").click()
        panel = page.get_by_role("complementary", name="Playback queue")
        await expect(panel.get_by_text("Your queue starts here")).to_be_visible()
        await page.get_by_role("button", name="Close playback queue").click()
        await expect(page.get_by_role("button", name="Show playback queue")).to_be_focused()
        await expect(page.get_by_text("65 matching songs", exact=True)).to_be_visible()
        await page.get_by_role("button", name="Show more tracks").click()
        await page.get_by_role("heading", name="Track 0060", exact=True).click()
        await page.get_by_role("button", name="Autoplay", exact=True).click()
        await page.get_by_role("button", name="Shuffle", exact=True).click()
        await page.get_by_role("button", name="Next song", exact=True).click()
        await page.get_by_role("button", name="Next song", exact=True).click()
        await page.get_by_role("button", name="Show playback queue").click()
        await expect(panel).to_be_visible()
        await expect(panel.get_by_role("tab")).to_have_count(0)
        await expect(panel.locator('[data-queue-state="upcoming"]')).to_have_count(40)
        await expect(panel.locator('[data-queue-state="past"]')).to_have_count(2)
        await expect(panel.locator('[aria-current="true"]')).to_have_count(1)
        assert await panel.locator("ol > li").evaluate_all(
            "rows => rows.map(row => row.dataset.queueState)",
        ) == ["past", "past", "current"] + ["upcoming"] * 40
        initial_queue = await queue_titles(page)
        source = await page.locator("audio").get_attribute("src")
        bookmark = page.url
        params = parse_qs(urlparse(bookmark).query)
        assert params["shuffle"] == ["1"] and params["autoplay"] == ["1"]
        assert params["anchor"] == [songs[60]["url"]] and params["position"] == ["2"]
        assert params["campaign"] == ["queue-test"]
        saved_history = await queue_titles(page, "past")
        await panel.get_by_role("button", name="Show more songs").click()
        await expect(panel.locator('[data-queue-state="upcoming"]')).to_have_count(64)
        names = await panel.locator('[data-queue-state="upcoming"] button').evaluate_all(
            "buttons => buttons.map(button => button.getAttribute('aria-label'))",
        )
        assert len(set(names)) == 64
        next_name = names[0]
        await panel.get_by_role("button", name=next_name, exact=True).click()
        expected_next = await page.locator("audio").get_attribute("src")

        # A fresh browser context proves the URL contains all state, without local storage.
        fresh = await browser.new_context(viewport={"width": 1600, "height": 1000})
        restarted_songs = [
            {**song, "id": f"restarted-{index}"}
            for index, song in enumerate(reversed(songs))
        ]
        await mock_library(fresh, restarted_songs)
        restored = await fresh.new_page()
        restored.on("pageerror", lambda error: errors.append(str(error)))
        await restored.goto(bookmark)
        await expect(restored.locator("audio")).to_have_attribute("src", source or "")
        await expect(restored.get_by_role("button", name="Next song")).to_be_enabled()
        await expect(
            restored.get_by_role("button", name="Autoplay", exact=True),
        ).to_have_attribute("aria-pressed", "true")
        await expect(
            restored.get_by_role("button", name="Shuffle", exact=True),
        ).to_have_attribute("aria-pressed", "true")
        await restored.get_by_role("button", name="Show playback queue").click()
        assert await queue_titles(restored) == initial_queue
        assert await queue_titles(restored, "past") == saved_history
        await restored.get_by_role("button", name="Next song", exact=True).click()
        await expect(restored.locator("audio")).to_have_attribute("src", expected_next or "")
        await restored.get_by_role("button", name="Previous song", exact=True).click()
        await expect(restored.locator("audio")).to_have_attribute("src", source or "")
        await restored.locator('[data-queue-state="past"]').get_by_role(
            "button", name="Play Track 0060", exact=True,
        ).click()
        await expect(restored.locator("audio")).to_have_attribute(
            "src", "http://127.0.0.1:5173/audio/Track%200060",
        )
        await restored.get_by_role("button", name="Next song", exact=True).click()
        await restored.get_by_role("button", name="Next song", exact=True).click()
        await expect(restored.locator("audio")).to_have_attribute("src", source or "")
        await restored.get_by_role("button", name="Close playback queue").click()
        await restored.get_by_role("button", name="Expand artwork", exact=True).click()
        await restored.get_by_role("button", name="Show playback queue").click()
        view = restored.get_by_role("region", name="Expanded artwork")
        bounds = await view.bounding_box()
        queue_bounds = await restored.locator("#playback-queue").bounding_box()
        assert bounds and queue_bounds and bounds["x"] + bounds["width"] <= queue_bounds["x"] + 1
        Path("dist").mkdir(exist_ok=True)
        await restored.screenshot(path="dist/playback-queue-desktop.png", animations="disabled")
        await restored.keyboard.press("Escape")
        await expect(restored.locator("#playback-queue")).to_have_count(0)
        await expect(view).to_be_visible()
        await restored.get_by_role("button", name="Show playback queue").click()
        await restored.set_viewport_size({"width": 390, "height": 844})
        await expect(
            restored.get_by_role("button", name="Close playback queue"),
        ).to_be_in_viewport()
        await expect(
            restored.get_by_role("button", name="Next song", exact=True),
        ).to_be_in_viewport()
        await restored.screenshot(path="dist/playback-queue-mobile.png", animations="disabled")
        assert await restored.evaluate(
            "document.documentElement.scrollWidth <= innerWidth",
        )
        current = restored.locator('#queue-tracks [aria-current="true"]')
        await expect(current).to_be_in_viewport()
        await restored.locator("#queue-tracks").evaluate(
            "list => { list.scrollTop = list.scrollHeight; }",
        )
        await expect(current).not_to_be_in_viewport()
        await restored.get_by_role("button", name="Jump to current song").click()
        await expect(current).to_be_in_viewport()
        scroll_position = await restored.evaluate("window.scrollY")
        for _ in range(20):
            await restored.get_by_role("button", name="Next song", exact=True).click()
            await expect(current).to_be_in_viewport()
        await expect(restored.locator('[data-queue-state="past"]')).to_have_count(5)
        await restored.get_by_role("button", name="Show earlier songs").click()
        await expect(restored.locator('[data-queue-state="past"]')).to_have_count(22)
        await restored.get_by_role("button", name="Jump to current song").click()
        await expect(current).to_be_in_viewport()
        assert await restored.evaluate("window.scrollY") == scroll_position
        await restored.locator('[data-queue-state="past"] button').first.focus()
        await restored.keyboard.press("Enter")
        await expect(restored.locator("audio")).to_have_attribute(
            "src", "http://127.0.0.1:5173/audio/Track%200060",
        )
        await restored.keyboard.press("Escape")
        await restored.keyboard.press("Escape")
        await restored.get_by_role("textbox", name="Search tracks").fill("Track 006")
        await expect(restored.get_by_text("6 matching songs", exact=True)).to_be_visible()
        await restored.locator("#statusFilter").select_option("all")
        filtered_bookmark = restored.url
        await restored.reload()
        await expect(
            restored.get_by_role("textbox", name="Search tracks"),
        ).to_have_value("Track 006")
        await expect(restored.locator("#statusFilter")).to_have_value("all")
        await expect(restored.get_by_text("6 matching songs", exact=True)).to_be_visible()
        assert parse_qs(urlparse(filtered_bookmark).query)["q"] == ["Track 006"]
        await restored.get_by_role("textbox", name="Search tracks").fill("no matches")
        await expect(restored.get_by_role("button", name="Next song")).to_be_disabled()
        await restored.get_by_role("button", name="Show playback queue").click()
        await expect(restored.get_by_text("Nothing up next", exact=True)).to_be_visible()

        # Navigation events restore mode and filters, while preserving unrelated URL state.
        await restored.evaluate("""url => {
            history.pushState(null, '', url + '#diagnostics');
            dispatchEvent(new PopStateEvent('popstate'));
        }""", bookmark)
        await expect(restored.get_by_role("textbox", name="Search tracks")).to_have_value("")
        await expect(restored.get_by_role("button", name="Next song")).to_be_enabled()
        assert urlparse(restored.url).fragment == "diagnostics"
        await restored.goto(
            "http://127.0.0.1:5173/?shuffle=wat&position=NaN"
            "&seed=Infinity&status=bad&track=missing",
        )
        await expect(restored.get_by_text("65 matching songs", exact=True)).to_be_visible()
        await expect(
            restored.get_by_role("button", name="Shuffle", exact=True),
        ).to_have_attribute("aria-pressed", "false")
        await restored.get_by_role("button", name="Next song", exact=True).click()
        await expect(restored.locator("audio")).to_have_attribute(
            "src", "http://127.0.0.1:5173/audio/Track%200064",
        )
        assert not errors, errors
        await browser.close()
    print(
        "Passed: fresh-context URL restore, restarted library IDs, stable shuffle "
        "and history, unified timeline, current-song scrolling, queue jumps, "
        "filters, malformed URLs, desktop/mobile layout, "
        "Escape and keyboard focus"
    )


if __name__ == "__main__":
    asyncio.run(main())
