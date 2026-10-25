"""Check quiet playback against Vite on port 5173 with real browser audio."""

import asyncio
import math
from pathlib import Path

from playwright.async_api import async_playwright, expect

from check_library_browser import track
from check_visualizer_browser import test_audio


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, channel="msedge",
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        page = await browser.new_page(viewport={"width": 2048, "height": 1157})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.route("**/library?*", lambda route: route.fulfill(json={
            "jobs": [track(0), track(1)], "total": 2, "next_offset": None,
        }))
        await page.route("**/jobs/*/thumbnail", lambda route: route.fulfill(status=204))
        audio_bytes = test_audio()
        await page.route("**/audio/*", lambda route: route.fulfill(
            content_type="audio/wav", body=audio_bytes,
        ))
        await page.goto("http://127.0.0.1:5173")
        await page.get_by_role("heading", name="Track 0000", exact=True).click()
        audio = page.locator("audio")
        await page.wait_for_function("!document.querySelector('audio').paused")
        volume = page.get_by_role("slider", name="Volume", exact=True)
        settings = page.get_by_role("button", name="Audio settings", exact=True)
        panel = page.get_by_role("dialog", name="Audio settings", exact=True)
        level = panel.get_by_role("spinbutton", name="Volume in decibels")

        async def set_decibels(value: int) -> None:
            await settings.click()
            await expect(level).to_be_focused()
            await level.press("ControlOrMeta+A")
            previous_volume = await audio.evaluate("audio => audio.volume")
            await level.press_sequentially(str(value))
            assert await audio.evaluate("audio => audio.volume") == previous_volume
            await level.press("Enter")
            await expect(settings).to_be_focused()
            await expect(panel).to_have_count(0)

        async def rms() -> float:
            return await page.evaluate("""async () => {
                const {getAudioAnalysis} = await import('/src/visualizer/audio.ts');
                const {analyser} = getAudioAnalysis(document.querySelector('audio'));
                await new Promise(resolve => setTimeout(resolve, 200));
                const samples = new Float32Array(analyser.fftSize);
                analyser.getFloatTimeDomainData(samples);
                return Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
            }""")

        await expect(page.get_by_role("spinbutton", name="Volume in decibels")).to_have_count(0)
        await expect(page.get_by_role("combobox", name="Volume preset")).to_have_count(0)
        await settings.click()
        await level.fill("-30")
        await level.press("Escape")
        await expect(panel).to_have_count(0)
        assert await audio.evaluate("audio => audio.volume") == 1
        await volume.press("End")
        await expect(volume).to_have_value("100")
        full_rms = await rms()
        assert full_rms > 0.1, full_rms
        await set_decibels(-40)
        await expect(volume).to_have_value("34")
        quiet_rms = await rms()
        assert math.isclose(quiet_rms / full_rms, 0.01, rel_tol=0.05), (
            full_rms, quiet_rms,
        )
        await volume.press("ArrowLeft")
        await expect(volume).to_have_value("33")
        assert math.isclose(await audio.evaluate("audio => audio.volume"), 10 ** (-60 * (1 - 32 / 99) / 20))
        await volume.press("Home")
        await expect(volume).to_have_value("0")
        assert await rms() < 1e-8
        await volume.press("ArrowRight")
        await expect(volume).to_have_value("1")
        assert math.isclose(await audio.evaluate("audio => audio.volume"), 0.001)
        low_rms = await rms()
        assert math.isclose(low_rms / full_rms, 0.001, rel_tol=0.05)
        await page.get_by_role("button", name="Mute", exact=True).click()
        assert await rms() < 1e-8
        await page.get_by_role("button", name="Unmute", exact=True).click()
        assert math.isclose(await audio.evaluate("audio => audio.volume"), 0.001)
        await set_decibels(-37)
        await expect(volume).to_have_value("39")
        await page.get_by_role("button", name="Next song", exact=True).click()
        await expect(volume).to_have_value("39")
        await page.get_by_role("button", name="Expand artwork", exact=True).click()
        await expect(volume).to_be_in_viewport()
        bounds = await volume.bounding_box()
        assert bounds and bounds["width"] >= 180, bounds
        output = Path("dist/volume-checks")
        output.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output / "artwork-desktop.png"))
        await volume.hover()
        await expect(page.get_by_role("group", name="Playback volume").locator("output")).to_have_css("opacity", "1")
        await settings.click()
        await page.screenshot(path=str(output / "audio-settings-desktop.png"))
        await page.get_by_role("heading", name="Track 0001", exact=True).click()
        await expect(panel).to_have_count(0)

        await page.get_by_role("button", name="Expand visualizer", exact=True).click()
        dialog = page.get_by_role("dialog", name="Music visualizer")
        await expect(dialog.get_by_role("slider", name="Volume", exact=True)).to_have_value("39")
        await dialog.get_by_role("button", name="Audio settings", exact=True).click()
        await dialog.get_by_role("spinbutton", name="Volume in decibels").fill("-24")
        await page.keyboard.press("Enter")
        await expect(dialog).to_be_visible()
        await expect(panel).to_have_count(0)
        await dialog.get_by_role("button", name="Audio settings", exact=True).click()
        await page.keyboard.press("Escape")
        await expect(dialog).to_be_visible()
        await dialog.get_by_role("button", name="Close visualizer").click()
        await expect(volume).to_have_value("60")

        await page.get_by_role("button", name="Mute", exact=True).click()
        await page.reload()
        await expect(page.get_by_role("button", name="Unmute", exact=True)).to_be_visible()
        await expect(volume).to_have_value("0")
        await page.get_by_role("heading", name="Track 0000", exact=True).click()
        assert await audio.evaluate("audio => audio.muted")
        await page.get_by_role("button", name="Unmute", exact=True).click()
        await expect(volume).to_have_value("60")
        await set_decibels(-40)
        await page.reload()
        await expect(volume).to_have_value("34")
        await page.get_by_role("heading", name="Track 0000", exact=True).click()
        await page.wait_for_function("!document.querySelector('audio').paused")
        assert math.isclose(await audio.evaluate("audio => audio.volume"), 0.01)

        for width in (1024, 768, 390):
            await page.set_viewport_size({"width": width, "height": 844})
            for control in (volume, settings):
                await expect(control).to_be_in_viewport()
                bounds = await control.bounding_box()
                assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
            assert await page.locator('[class*="nowPlayingDock"]').evaluate(
                "element => element.scrollWidth <= element.clientWidth",
            )
            await page.screenshot(path=str(output / f"width-{width}.png"))
            await settings.click()
            await expect(panel).to_be_in_viewport()
            bounds = await panel.bounding_box()
            assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
            await page.screenshot(path=str(output / f"settings-width-{width}.png"))
            await page.get_by_role("button", name="Close audio settings", exact=True).click()
        await page.screenshot(path=str(output / "mobile.png"))

        await page.evaluate("localStorage.setItem('twitch-spy.volume', JSON.stringify({volume: 0.4, muted: false}))")
        await page.reload()
        await expect(volume).to_have_value("87")
        assert await audio.evaluate("audio => audio.volume") == 0.4

        for invalid in ('null', '{"volume": 9, "muted": false}', '{broken'):
            await page.evaluate("value => localStorage.setItem('twitch-spy.volume', value)", invalid)
            await page.reload()
            await expect(volume).to_have_value("100")
        await page.add_init_script("""
            Storage.prototype.setItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
            Storage.prototype.getItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
        """)
        await page.reload()
        await set_decibels(-40)
        assert math.isclose(await audio.evaluate("audio => audio.volume"), 0.01)
        assert not errors, errors
        await browser.close()
        print(f"Volume checks passed: measured quiet/full RMS {quiet_rms / full_rms:.4f}, "
              "0-100% slider, -60 dB attenuation, silence, settings dismissal/focus, shared visualizer, "
              "track changes, saved-level compatibility, reload, mobile, and unavailable/invalid storage.")


if __name__ == "__main__":
    asyncio.run(main())
