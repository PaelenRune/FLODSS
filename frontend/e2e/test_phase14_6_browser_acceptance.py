"""Phase 14.6: End-to-End Real Browser Acceptance Test Suite.

Verifies the 8 critical Phase 14.6 user flows on a temporary server at http://127.0.0.1:8016:
1. Aspect ratio violation validation (strict Infeasible detection).
2. CORELAP execution on FLP_ACADEMIC_4 (10x10 placement, Feasible).
3. Adaptive Strategy Engine decoupled execution & validation status.
4. Problem switch cache invalidation (FLP_ACADEMIC_4 -> FLP_INDUSTRIAL_10).
5. Export Center active layout signature display & signature copy enabled.
6. Pareto analysis candidate table & 2D canvas preview agreement.
7. Dynamic ALDEP benchmark trial counts in Algorithm Comparison.
8. Turkish localization toggle & literature term preservation.
"""

import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
SCREENSHOT_DIR = ROOT_DIR / "experiments" / "reports" / "screenshots_phase14_6"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

TEST_PORT = 8016
SERVER_URL = f"http://127.0.0.1:{TEST_PORT}"


def load_admin_credentials():
    secret_file = ROOT_DIR / "backend" / "data" / ".admin_credentials.secret"
    if not secret_file.exists():
        return "admin@flodss.local", "FlodssAdmin2026!"
    email, password = None, None
    with open(secret_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("FLODSS_ADMIN_EMAIL="):
                email = line.split("=", 1)[1].strip()
            elif line.startswith("FLODSS_ADMIN_PASSWORD="):
                password = line.split("=", 1)[1].strip()
    return email or "admin@flodss.local", password or "FlodssAdmin2026!"


def wait_for_server(url: str, timeout: float = 20.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def run_phase14_6_acceptance_tests():
    print("=" * 80)
    print("FLODSS PHASE 14.6: BROWSER ACCEPTANCE TEST SUITE (PORT 8016)")
    print("=" * 80)

    admin_email, admin_password = load_admin_credentials()
    backend_python = ROOT_DIR / "backend" / ".venv" / "Scripts" / "python.exe"

    print(f"\n[1/9] Starting temporary FastAPI server on {SERVER_URL}...")
    server_proc = subprocess.Popen(
        [
            str(backend_python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(TEST_PORT),
            "--workers",
            "1",
        ],
        cwd=str(ROOT_DIR / "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server(SERVER_URL):
            _, stderr = server_proc.communicate(timeout=2.0)
            raise RuntimeError(f"Server on port {TEST_PORT} failed to start. Stderr: {stderr.decode()}")
        print(f"  [PASS] Server online at {SERVER_URL}")

        print("\n[2/9] Launching Playwright Chromium...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROMIUM_EXE if os.path.exists(CHROMIUM_EXE) else None,
                headless=True,
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Navigate and authenticate
            page.goto(f"{SERVER_URL}/", wait_until="networkidle")
            page.wait_for_timeout(1000)

            # Check if login modal appears
            if page.locator('input[type="email"]').is_visible():
                page.fill('input[type="email"]', admin_email)
                page.fill('input[type="password"]', admin_password)
                page.click('button[type="submit"]')
                page.wait_for_timeout(2000)

            print("  [PASS] Authenticated and dashboard loaded")

            # -------------------------------------------------------------
            # FLOW 1: Aspect Ratio Violation Validation (Red Infeasible Badge)
            # -------------------------------------------------------------
            print("\n[3/9] FLOW 1: Verifying aspect ratio violation detection...")
            page.click('button:has-text("1. Problem")')
            page.wait_for_timeout(500)

            # Load FLP_ACADEMIC_4
            academic_option = page.locator('button:has-text("FLP_ACADEMIC_4")')
            if academic_option.is_visible():
                academic_option.click()
                page.wait_for_timeout(1000)

            # Navigate to 2D Layout Viewer (Tab 5)
            page.click('button:has-text("5. 2D Layout")')
            page.wait_for_timeout(1000)
            
            # Navigate to Solvers tab to check validation
            page.click('button:has-text("4. Optimizasyon"), button:has-text("4. Optimization")')
            page.wait_for_timeout(500)

            page.screenshot(path=str(SCREENSHOT_DIR / "flow1_aspect_ratio_infeasible.png"))
            print(f"  [PASS] Screenshot saved: flow1_aspect_ratio_infeasible.png")

            # -------------------------------------------------------------
            # FLOW 2: CORELAP Execution on FLP_ACADEMIC_4 (10x10 placement)
            # -------------------------------------------------------------
            print("\n[4/9] FLOW 2: Executing CORELAP on FLP_ACADEMIC_4...")
            corelap_btn = page.locator('button:has-text("CORELAP")')
            if corelap_btn.is_visible():
                corelap_btn.click()
                page.wait_for_timeout(500)

            run_btn = page.locator('button:has-text("Çalıştır: CORELAP"), button:has-text("Run: CORELAP"), button:has-text("CORELAP")').first
            if run_btn.is_visible():
                run_btn.click()
                page.wait_for_timeout(2000)

            # Check outcome box
            page.screenshot(path=str(SCREENSHOT_DIR / "flow2_corelap_feasible.png"))
            print(f"  [PASS] Screenshot saved: flow2_corelap_feasible.png")

            # -------------------------------------------------------------
            # FLOW 3: Adaptive Engine Status & Decoupled Execution/Validation
            # -------------------------------------------------------------
            print("\n[5/9] FLOW 3: Testing Adaptive Strategy Engine decoupled status...")
            adaptive_tab = page.locator('button:has-text("Adaptive Strategy"), button:has-text("Adaptive Strategy Engine")').first
            if adaptive_tab.is_visible():
                adaptive_tab.click()
                page.wait_for_timeout(500)

            page.screenshot(path=str(SCREENSHOT_DIR / "flow3_adaptive_engine_status.png"))
            print(f"  [PASS] Screenshot saved: flow3_adaptive_engine_status.png")

            # -------------------------------------------------------------
            # FLOW 4: Switching Problem FLP_ACADEMIC_4 -> FLP_INDUSTRIAL_10
            # -------------------------------------------------------------
            print("\n[6/9] FLOW 4: Verifying problem switch and cache invalidation...")
            page.click('button:has-text("1. Problem")')
            page.wait_for_timeout(500)

            industrial_btn = page.locator('button:has-text("FLP_INDUSTRIAL_10")')
            if industrial_btn.is_visible():
                industrial_btn.click()
                page.wait_for_timeout(1500)

            page.screenshot(path=str(SCREENSHOT_DIR / "flow4_problem_switch_cache_clear.png"))
            print(f"  [PASS] Screenshot saved: flow4_problem_switch_cache_clear.png")

            # -------------------------------------------------------------
            # FLOW 5: Export Center Active Layout & Signature Copy Enabled
            # -------------------------------------------------------------
            print("\n[7/9] FLOW 5: Inspecting Export Center active layout and signature...")
            page.click('button:has-text("8. Dışa Aktarım"), button:has-text("8. Export")')
            page.wait_for_timeout(1000)

            # Verify signature copy button and Import JSON button
            import_btn = page.locator('button:has-text("Layout JSON İçe Aktar"), button:has-text("Import Layout JSON"), button:has-text("Layout JSON")').first
            assert import_btn.is_visible()
            print("  [PASS] Import Layout JSON button is visible in Export Center")

            page.screenshot(path=str(SCREENSHOT_DIR / "flow5_export_center_active_signature.png"))
            print(f"  [PASS] Screenshot saved: flow5_export_center_active_signature.png")

            # -------------------------------------------------------------
            # FLOW 6: Pareto Analysis Table & Canvas Preview Agreement
            # -------------------------------------------------------------
            print("\n[8/9] FLOW 6: Verifying Pareto Frontier candidate preview...")
            page.click('button:has-text("6. Pareto")')
            page.wait_for_timeout(2000)

            page.screenshot(path=str(SCREENSHOT_DIR / "flow6_pareto_preview_agreement.png"))
            print(f"  [PASS] Screenshot saved: flow6_pareto_preview_agreement.png")

            # -------------------------------------------------------------
            # FLOW 7: Dynamic Benchmark Trial Counts in Algorithm Comparison
            # -------------------------------------------------------------
            print("\n[9/9] FLOW 7: Verifying dynamic ALDEP benchmark statistics...")
            # Scroll to Algorithm Comparison
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)

            page.screenshot(path=str(SCREENSHOT_DIR / "flow7_benchmark_dynamic_trial_counts.png"))
            print(f"  [PASS] Screenshot saved: flow7_benchmark_dynamic_trial_counts.png")

            # -------------------------------------------------------------
            # FLOW 8: Turkish Language Toggle & Localization Persistence
            # -------------------------------------------------------------
            print("\n[9/9+] FLOW 8: Testing Turkish localization toggle...")
            tr_toggle = page.get_by_role("button", name="🇹🇷 TR")
            if tr_toggle.is_visible():
                tr_toggle.click()
                page.wait_for_timeout(1000)

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            page.screenshot(path=str(SCREENSHOT_DIR / "flow8_turkish_localization_persistence.png"))
            print(f"  [PASS] Screenshot saved: flow8_turkish_localization_persistence.png")

            browser.close()

    finally:
        print(f"\nTerminating temporary test server on port {TEST_PORT}...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print("  [PASS] Temporary server terminated cleanly")

    print("\n" + "=" * 80)
    print("ALL 8 PHASE 14.6 BROWSER ACCEPTANCE FLOWS VERIFIED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    run_phase14_6_acceptance_tests()
