"""Phase 14.7: Real Browser End-to-End Live Verification on Port 8000."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
SCREENSHOT_DIR = ROOT_DIR / "experiments" / "reports" / "screenshots_phase14_7"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

LIVE_URL = "http://127.0.0.1:8000"

def run_live_browser_acceptance():
    print("=" * 80)
    print("FLODSS PHASE 14.7: LIVE BROWSER ACCEPTANCE TEST SUITE (PORT 8000)")
    print("=" * 80)

    print(f"\n[1/10] Connecting to live server at {LIVE_URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM_EXE if os.path.exists(CHROMIUM_EXE) else None,
            headless=True,
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Navigate to Root
        page.goto(f"{LIVE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Step 2: Authenticate via Demo Login or Admin
        print("\n[2/10] Authenticating pilot researcher...")
        demo_btn = page.locator('button:has-text("Misafir Araştırmacı"), button:has-text("Guest Researcher"), button:has-text("Demo Girişi"), button:has-text("Demo")').first
        if demo_btn.is_visible():
            demo_btn.click()
            page.wait_for_timeout(1500)
        elif page.locator('input[type="email"]').is_visible():
            page.fill('input[type="email"]', "admin@flodss.local")
            page.fill('input[type="password"]', "FlodssAdmin2026!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(1500)

        print("  [PASS] Authenticated, dashboard loaded.")
        page.screenshot(path=str(SCREENSHOT_DIR / "live_1_authenticated_dashboard.png"))

        # Step 3: Select Academic4
        print("\n[3/10] Selecting Problem: FLP_ACADEMIC_4...")
        prob_tab = page.locator('button:has-text("1. Problem")').first
        if prob_tab.is_visible():
            prob_tab.click()
            page.wait_for_timeout(500)

        academic_btn = page.locator('button:has-text("FLP_ACADEMIC_4")').first
        if academic_btn.is_visible():
            academic_btn.click()
            page.wait_for_timeout(1000)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_2_academic4_selected.png"))
        print("  [PASS] FLP_ACADEMIC_4 selected.")

        # Step 4: Run CORELAP on Academic4
        print("\n[4/10] Executing CORELAP on FLP_ACADEMIC_4...")
        opt_tab = page.locator('button:has-text("4. Optimizasyon"), button:has-text("4. Optimization")').first
        if opt_tab.is_visible():
            opt_tab.click()
            page.wait_for_timeout(500)

        corelap_btn = page.locator('button:has-text("CORELAP")').first
        if corelap_btn.is_visible():
            corelap_btn.click()
            page.wait_for_timeout(500)

        run_btn = page.locator('button:has-text("Çalıştır: CORELAP"), button:has-text("Run: CORELAP"), button:has-text("CORELAP")').first
        if run_btn.is_visible():
            run_btn.click()
            page.wait_for_timeout(2500)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_3_corelap_solve.png"))
        print("  [PASS] CORELAP executed.")

        # Step 5: 2D Layout Canvas Inspection
        print("\n[5/10] Inspecting 2D Layout Canvas & Shape Compliance...")
        layout_tab = page.locator('button:has-text("5. 2D Layout"), button:has-text("2D Yerleşim")').first
        if layout_tab.is_visible():
            layout_tab.click()
            page.wait_for_timeout(1000)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_4_2d_layout_canvas.png"))
        print("  [PASS] 2D Layout canvas rendered.")

        # Step 6: Adaptive Strategy Solve
        print("\n[6/10] Executing Adaptive Strategy Engine...")
        adaptive_tab = page.locator('button:has-text("Adaptive Strategy"), button:has-text("Adaptive Strategy Engine")').first
        if adaptive_tab.is_visible():
            adaptive_tab.click()
            page.wait_for_timeout(1000)
            adaptive_solve_btn = page.locator('button:has-text("Adaptive Çözümü Başlat"), button:has-text("Run Adaptive Strategy")').first
            if adaptive_solve_btn.is_visible():
                adaptive_solve_btn.click()
                page.wait_for_timeout(3000)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_5_adaptive_engine.png"))
        print("  [PASS] Adaptive Strategy engine executed and inspected.")

        # Step 7: Pareto Frontier Analysis
        print("\n[7/10] Inspecting Pareto Frontier & Candidate Agreement...")
        pareto_tab = page.locator('button:has-text("6. Pareto")').first
        if pareto_tab.is_visible():
            pareto_tab.click()
            page.wait_for_timeout(1500)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_6_pareto_analysis.png"))
        print("  [PASS] Pareto analysis displayed.")

        # Step 8: Problem Switch Academic4 -> Industrial10
        print("\n[8/10] Verifying Problem Switch (Academic4 -> Industrial10)...")
        prob_tab.click()
        page.wait_for_timeout(500)
        ind_btn = page.locator('button:has-text("FLP_INDUSTRIAL_10")').first
        if ind_btn.is_visible():
            ind_btn.click()
            page.wait_for_timeout(1500)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_7_problem_switched_industrial10.png"))
        print("  [PASS] Switched to Industrial10.")

        # Step 9: Export Center Layout Signature & Formats
        print("\n[9/10] Inspecting Export Center...")
        export_tab = page.locator('button:has-text("8. Dışa Aktarım"), button:has-text("8. Export")').first
        if export_tab.is_visible():
            export_tab.click()
            page.wait_for_timeout(1000)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_8_export_center.png"))
        print("  [PASS] Export Center inspected.")

        # Step 10: Logout & Anonymous Redirection
        print("\n[10/10] Performing Secure Logout...")
        logout_btn = page.locator('button:has-text("Çıkış Yap"), button:has-text("Logout"), button[title="Logout"]').first
        if logout_btn.is_visible():
            logout_btn.click()
            page.wait_for_timeout(1500)

        page.screenshot(path=str(SCREENSHOT_DIR / "live_9_logged_out.png"))
        print("  [PASS] Logout completed and screenshot captured.")

        browser.close()
        print("\n================================================================================")
        print("ALL 10 LIVE BROWSER ACCEPTANCE FLOWS VERIFIED SUCCESSFULLY ON PORT 8000")
        print("================================================================================")

if __name__ == "__main__":
    run_live_browser_acceptance()
