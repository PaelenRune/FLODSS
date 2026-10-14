import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
LOCAL_URL = "http://127.0.0.1:8000"

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=CHROMIUM_EXE,
        headless=True,
    )
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    page = ctx.new_page()

    page.on("console", lambda msg: print(f"  [CONSOLE] {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"  [PAGE ERROR] {err}"))

    page.goto(f"{LOCAL_URL}/", wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    demo_btn = page.locator('button:has-text("Misafir Araştırmacı"), button:has-text("Guest Researcher"), button:has-text("Demo Girişi"), button:has-text("Demo")').first
    if demo_btn.is_visible():
        demo_btn.click()
        page.wait_for_timeout(1500)

    # Go to Layout tab
    btn = page.locator('button[data-testid="tab-layout"]').first
    btn.click(force=True)
    page.wait_for_timeout(1500)

    svg = page.locator('[data-testid="layout-canvas-svg"]').first
    print("SVG visible:", svg.is_visible())
    
    png_btn = page.locator('button[data-testid="export-layout-png-btn"]').first
    print("PNG btn visible:", png_btn.is_visible())

    print("Triggering download...")
    with page.expect_download(timeout=10000) as download_info:
        png_btn.click(force=True)

    download = download_info.value
    out = ROOT_DIR / "experiments" / "reports" / "screenshots_phase15_2_1" / "test_debug.png"
    download.save_as(str(out))
    print(f"Downloaded successfully: {out.stat().st_size} bytes")

    with open(out, "rb") as f:
        data = f.read()
    phys_idx = data.find(b"pHYs")
    print(f"pHYs index: {phys_idx}")
    if phys_idx != -1:
        phys_data = data[phys_idx + 4:phys_idx + 13]
        x_ppm = int.from_bytes(phys_data[0:4], "big")
        y_ppm = int.from_bytes(phys_data[4:8], "big")
        print(f"DPI: {round(x_ppm * 0.0254)} x {round(y_ppm * 0.0254)}")

    browser.close()
