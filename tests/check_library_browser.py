"""Run against Vite on port 5173: uv run --with playwright python tests/check_library_browser.py."""

import asyncio
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Route, async_playwright, expect


HARNESS = """
import React from '/node_modules/.vite/deps/react.js';
import JobList from '/src/components/JobList.tsx';
import JobOverview from '/src/components/JobOverview.tsx';
const handlers = new Map();
window.testSocket = {
    connected: true,
    sent: [],
    on(name, handler) {
        if (!handlers.has(name)) handlers.set(name, new Set());
        handlers.get(name).add(handler);
    },
    off(name, handler) { handlers.get(name)?.delete(handler); },
    emit(name) { this.sent.push(name); },
    receive(name, data) { handlers.get(name)?.forEach(fn => fn(data)); },
};
export default function App() {
    return React.createElement(React.Fragment, null,
        React.createElement(JobOverview, {socket: window.testSocket}),
        React.createElement(JobList, {
            socket: window.testSocket,
            onMusicSelected: job => { window.selectedTrack = job; },
        })
    );
}
"""


def track(index: int) -> dict[str, object]:
    return {
        "id": str(index), "url": f"https://youtube.com/watch?v={index}",
        "content_name": f"Track {index:04d}", "status": "finished",
        "content_type": "AUDIO", "platform": "YOUTUBE", "single_item": True,
        "url_valid": True, "download_dir": "music",
        "thumbnail_url": f"/jobs/{index}/thumbnail",
    }


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page(viewport={"width": 1366, "height": 768})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.route("**/src/App.tsx", lambda route: route.fulfill(
            content_type="application/javascript", body=HARNESS,
        ))
        artwork: list[str] = []

        async def thumbnail(route: Route) -> None:
            artwork.append(route.request.url)
            await route.fulfill(status=204)

        await page.route("**/jobs/*/thumbnail", thumbnail)
        held: list[Route] = []
        hold_pages = True
        fail_pages = False

        async def fulfill_page(route: Route) -> None:
            offset = int(parse_qs(urlparse(route.request.url).query)["offset"][0])
            end = min(offset + 48, 1622)
            await route.fulfill(json={
                "jobs": [track(index) for index in range(offset, end)],
                "total": 1622, "next_offset": end if end < 1622 else None,
            })

        async def library(route: Route) -> None:
            if hold_pages:
                held.append(route)
            elif fail_pages:
                await route.fulfill(status=503)
            else:
                await fulfill_page(route)

        await page.route("**/library?*", library)

        async def next_request() -> Route:
            for _ in range(100):
                if held:
                    return held.pop(0)
                await page.wait_for_timeout(20)
            raise AssertionError("No library request arrived")

        await page.goto("http://127.0.0.1:5173")
        await expect(page.get_by_text("Loading your first tracks…")).to_be_visible()
        await expect(page.locator('[class*="skeletonCard"]')).to_have_count(6)
        # StrictMode aborts the first mount's request; fulfill all initial requests.
        await page.wait_for_timeout(200)
        for route in list(held):
            await fulfill_page(route)
            held.remove(route)
        await expect(page.get_by_role("heading", name="Track 0000", exact=True)).to_be_visible()
        await expect(page.locator('[role="button"]')).to_have_count(48)
        second = await next_request()
        await expect(page.get_by_role("status")).to_contain_text("48 of 1622")
        await page.get_by_role("button", name="Track Finished Track 0000", exact=False).click()
        assert await page.evaluate("window.selectedTrack.id") == "0"
        assert len(artwork) < 48, len(artwork)

        # A live change must win over later pages, including the final snapshot.
        updated = {**track(0), "content_name": "Live title", "status": "failed"}
        await page.evaluate("job => testSocket.receive('atom_update_status', job)", updated)
        await expect(page.get_by_role("heading", name="Track 0000", exact=True)).to_have_count(0)
        await page.get_by_role("textbox", name="Search tracks").fill("Track 1621")
        await expect(page.get_by_text("Looking for matching tracks…")).to_be_visible()
        hold_pages = False
        await fulfill_page(second)
        await expect(page.get_by_role("heading", name="Track 1621", exact=True)).to_be_visible(timeout=15000)
        await expect(page.get_by_role("status")).to_have_count(0)
        await page.get_by_role("textbox", name="Search tracks").fill("")
        await expect(page.locator('[role="button"]')).to_have_count(48)
        await page.get_by_role("button", name="Show more tracks").click()
        await expect(page.locator('[role="button"]')).to_have_count(96)
        await page.locator("#statusFilter").select_option("failed")
        await expect(page.get_by_role("heading", name="Live title", exact=True)).to_be_visible()

        # Reconnection retains cards, partial failures remain actionable, retry recovers.
        await page.locator("#statusFilter").select_option("finished")
        hold_pages = True
        await page.evaluate("testSocket.receive('connect')")
        await expect(page.locator('[role="button"]')).to_have_count(48)
        first = await next_request()
        hold_pages = False
        fail_pages = True
        await fulfill_page(first)
        await expect(page.get_by_role("alert")).to_be_visible()
        await expect(page.locator('[role="button"]')).to_have_count(48)
        fail_pages = False
        await page.get_by_role("button", name="Retry loading").click()
        await expect(page.get_by_role("alert")).to_have_count(0)
        await expect(page.get_by_role("status")).to_have_count(0, timeout=15000)
        assert "request_initial_data" not in await page.evaluate("testSocket.sent")
        assert "request_statistics" in await page.evaluate("testSocket.sent")
        assert not errors, errors
        await page.screenshot(path="dist/library-progressive-preview.png")
        await browser.close()
        print("Passed: 1622 tracks, progressive rendering, lazy artwork, search, live updates, show more, reconnect and retry")


if __name__ == "__main__":
    asyncio.run(main())
