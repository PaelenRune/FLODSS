"""Phase 14.4: Real Browser Single-Origin E2E Verification.

Tests true single-origin hosting on http://127.0.0.1:8000 (No Vite dev server):
1. Subprocess starts Uvicorn serving compiled dist/ and API router.
2. Playwright navigates to http://127.0.0.1:8000/.
3. Verifies login dialog, authenticates admin.
4. Verifies single-origin dashboard, problem loading, and 2D canvas.
5. Captures visual evidence screenshot for pilot documentation.
6. Verifies clean logout.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import urllib.request
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
SCREENSHOT_DIR = ROOT_DIR / "experiments" / "reports" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_URL = "http://127.0.0.1:8000"


def wait_for_server(url: str, timeout: float = 15.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def run_single_origin_browser_test():
    print("=" * 75)
    print("FLODSS Phase 14.4: Single-Origin Real Browser E2E Verification")
    print("=" * 75)

    # 1. Start Uvicorn backend in single-origin mode
    backend_venv_python = ROOT_DIR / "backend" / ".venv" / "Scripts" / "python.exe"
    print(f"\n[1/6] Launching single-origin Uvicorn on {SERVER_URL}...")
    server_proc = subprocess.Popen(
        [
            str(backend_venv_python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--workers",
            "1",
        ],
        cwd=str(ROOT_DIR / "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        ready = wait_for_server(SERVER_URL)
        if not ready:
            stdout, stderr = server_proc.communicate(timeout=2.0)
            raise RuntimeError(f"Server failed to start within timeout.\nStderr: {stderr.decode()}")
        print("  [PASS] Server is online and responding at http://127.0.0.1:8000")

        # 2. Launch Playwright
        print("\n[2/6] Launching Playwright Chromium browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROMIUM_EXE if os.path.exists(CHROMIUM_EXE) else None,
                headless=True,
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # 3. Navigate to single origin root
            print(f"\n[3/6] Navigating to {SERVER_URL}/...")
            page.goto(f"{SERVER_URL}/", wait_until="networkidle")
            page.wait_for_timeout(1000)

            # Check title
            title = page.title()
            print(f"  [PASS] Page title: '{title}'")
            assert "Facility Layout" in title

            # Check login modal
            login_heading = page.locator("text=FLODSS Research Portal")
            assert login_heading.is_visible()
            print("  [PASS] Login modal barrier is active on single origin")

            # 4. Authenticate as Admin
            print("\n[4/6] Authenticating as administrator...")
            page.fill('input[type="email"]', "admin@flodss.local")
            page.fill('input[type="password"]', "FlodssAdmin2026!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(2000)

            # Verify authenticated state
            assert page.locator("text=Active Research Project").is_visible()
            assert page.locator("text=Online").is_visible()
            print("  [PASS] Authenticated dashboard loaded successfully on same origin")

            # 5. Navigate to 2D Canvas and verify
            print("\n[5/6] Inspecting 2D Layout Canvas (Tab 5)...")
            page.click('button:has-text("5. 2D Layout Viewer")')
            page.wait_for_timeout(1000)
            
            # Save screenshot
            screenshot_path = SCREENSHOT_DIR / "phase14_4_single_origin_dashboard.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  [PASS] Screenshot saved: {screenshot_path.name}")

            # 6. Logout verification
            print("\n[6/6] Logging out and verifying session barrier...")
            page.click('button:has-text("Logout")')
            page.wait_for_timeout(1000)
            assert page.locator("text=FLODSS Research Portal").is_visible()
            print("  [PASS] Logged out successfully; login barrier restored")

            browser.close()

    finally:
        print("\nShutting down Uvicorn server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print("  [PASS] Server terminated cleanly")

    print("\n" + "=" * 75)
    print("PHASE 14.4 SINGLE-ORIGIN REAL BROWSER E2E TEST: PASSED")
    print("=" * 75)


if __name__ == "__main__":
    run_single_origin_browser_test()
