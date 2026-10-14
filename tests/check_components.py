"""Check responsive sync controls against Vite: make check-components."""

from pathlib import Path
from playwright.sync_api import sync_playwright

output_dir = Path(__file__).resolve().parents[1] / "dist"
output_dir.mkdir(exist_ok=True)
plan = {
    'dirs_to_create': ['/sdcard/Music/Albums'],
    'files_to_transfer': [dict(local_path=f'/music/{i}.mp3', remote_path=f'/sdcard/Music/Albums/{i}.mp3', filename=f'Track {i} with a long descriptive title.mp3', size_bytes=123456) for i in range(150)],
    'skipped_count': 1622,
    'total_transfer_bytes': 18518400,
}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='msedge')
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/sync/devices', lambda r: r.fulfill(json={'connected': True, 'devices': ['RFCW70Y98TD']}))
    page.route('**/sync/plan', lambda r: r.fulfill(json=plan))
    page.route('**/socket.io/**', lambda r: r.abort())
    for width, height in [(1920,1080), (1440,900), (1366,768), (1280,720), (1024,640), (390,844)]:
        page.set_viewport_size({'width':width, 'height':height})
        page.goto('http://127.0.0.1:5173')
        launch = page.get_by_role('button', name='Sync to device', exact=True)
        launch.wait_for()
        sidebar = page.locator('aside').evaluate('(e) => ({height:e.clientHeight, scroll:e.scrollHeight})')
        if width > 900:
            assert sidebar['scroll'] <= sidebar['height'] + 1, (width, height, sidebar)
            assert launch.evaluate('(e) => e.getBoundingClientRect().bottom <= innerHeight')
        launch.click()
        page.get_by_role('button', name='Scan for device').click()
        page.get_by_role('button', name='Plan sync', exact=True).click()
        confirm = page.get_by_role('button', name='Confirm sync', exact=False)
        confirm.wait_for()
        assert confirm.evaluate('(e) => {const r=e.getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0}'), (width,height)
        dialog = page.get_by_role('dialog')
        assert dialog.evaluate('(e) => e.scrollHeight <= e.clientHeight + 1'), (width,height,'dialog scrolls')
        assert dialog.evaluate('(e) => e.getBoundingClientRect().right <= innerWidth')
        if width == 1366:
            page.screenshot(path=str(output_dir / 'sync-review-preview.png'))
        page.keyboard.press('Escape')
        assert not dialog.is_visible()
        assert launch.evaluate('(e) => e === document.activeElement')
        launch.click()
        assert confirm.is_visible()
        print(f'{width}x{height}: sidebar and sync review passed')
    assert not errors, errors
    browser.close()
