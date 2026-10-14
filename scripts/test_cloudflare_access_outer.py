import os
from pathlib import Path
from playwright.sync_api import sync_playwright

CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
TARGET_URL = "https://ranch-laboratory-gravity-conservation.trycloudflare.com"

print(f"Connecting to live Cloudflare URL: {TARGET_URL}...")
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=CHROMIUM_EXE if os.path.exists(CHROMIUM_EXE) else None,
        headless=True,
    )
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    try:
        print("Page Title:", page.title().encode("ascii", "replace").decode("ascii"))
    except Exception:
        pass
    print("Page URL:", page.url)

    # Screenshot initial Cloudflare barrier
    ss_dir = Path("experiments/reports/screenshots_final_audit")
    ss_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(ss_dir / "cloudflare_barrier_initial.png"))

    email_input = page.locator('input[type="email"], input[name="email"]')
    if email_input.is_visible():
        print("[CHECK 1: PASS] Cloudflare Access OTP barrier is rendered.")
        print("Testing unauthorized email rejection...")
        email_input.fill("unauthorized_intruder@attacker-domain.org")
        page.screenshot(path=str(ss_dir / "cloudflare_unauthorized_filled.png"))

        submit_btn = page.locator('button[type="submit"]').first
        if submit_btn.is_visible():
            submit_btn.click()
            page.wait_for_timeout(3500)
            page.screenshot(path=str(ss_dir / "cloudflare_unauthorized_result.png"))

            body_text = page.locator("body").inner_text()
            print("Response text summary after unauthorized submit:")
            for line in body_text.splitlines():
                if any(k in line.lower() for k in ["error", "denied", "authorized", "code", "pin", "invalid", "access"]):
                    print("  ->", line.strip())

    browser.close()
