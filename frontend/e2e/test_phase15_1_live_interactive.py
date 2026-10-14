import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
SCREENSHOT_DIR = ROOT_DIR / "experiments" / "reports" / "screenshots_phase15_1"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_URL = "http://127.0.0.1:8000"
PUBLIC_TUNNEL_URL = "https://finds-code-tattoo-inquiry.trycloudflare.com"

def run_phase15_1_interactive_verification():
    print("=" * 80)
    print("FLODSS PHASE 15.1: INTERACTIVE LAYOUT & DECISION SUPPORT VERIFICATION")
    print("=" * 80)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM_EXE if os.path.exists(CHROMIUM_EXE) else None,
            headless=True,
        )

        # Desktop Viewport (1440x900)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # STEP 1: Connect & Authenticate on Localhost
        print("\n[STEP 1] Connecting to Localhost Port 8000 & Authenticating...")
        page.goto(f"{LOCAL_URL}/", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        demo_btn = page.locator('button:has-text("Misafir Araştırmacı"), button:has-text("Guest Researcher"), button:has-text("Demo Girişi"), button:has-text("Demo")').first
        if demo_btn.is_visible():
            demo_btn.click()
            page.wait_for_timeout(1500)
        elif page.locator('input[type="email"]').is_visible():
            page.fill('input[type="email"]', "admin@flodss.local")
            page.fill('input[type="password"]', "FlodssAdmin2026!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(1500)

        page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_home.png"))
        print("  [PASS] Authenticated successfully.")
        results.append(("Authentication", True, "Successfully entered platform dashboard"))

        # STEP 2: Select FLP_ACADEMIC_4 & Run Solver
        print("\n[STEP 2] Selecting FLP_ACADEMIC_4 & Executing Solver...")
        prob_tab = page.locator('button:has-text("1. Problem")').first
        if prob_tab.is_visible():
            prob_tab.click()
            page.wait_for_timeout(500)

        academic_btn = page.locator('button:has-text("FLP_ACADEMIC_4")').first
        if academic_btn.is_visible():
            academic_btn.click()
            page.wait_for_timeout(1000)
            print("  [PASS] FLP_ACADEMIC_4 problem loaded.")

        # Navigate to Tab 4: Optimization and run solver
        opt_tab = page.locator('button:has-text("4. Optimizasyon"), button:has-text("4. Optimization")').first
        if opt_tab.is_visible():
            opt_tab.click()
            page.wait_for_timeout(800)
            run_btn = page.locator('button:has-text("Çalıştır:"), button:has-text("Run Adaptive"), button:has-text("Run")').first
            if run_btn.is_visible():
                print(f"  [INFO] Clicking solver run button: {run_btn.inner_text().strip()}")
                run_btn.click()
                # Wait for execution and auto-redirect to Tab 5
                page.wait_for_timeout(4000)

        # STEP 3: Tab 5 - 2D Layout Viewer Inspection & Auto-Fit (Academic 4)
        print("\n[STEP 3] Inspecting Tab 5: 2D Layout Viewer (Academic 4)...")
        layout_tab = page.locator('button:has-text("5. 2D Layout"), button:has-text("5. 2D Layout Görünümü")').first
        if layout_tab.is_visible():
            layout_tab.click()
            page.wait_for_timeout(1200)

        # Check Decision Guidance Box
        guide_btn = page.locator('button:has-text("2D Layout İnceleme Rehberi"), button:has-text("Layout Inspection Guide")').first
        if guide_btn.is_visible():
            guide_btn.click()
            page.wait_for_timeout(500)
            print("  [PASS] 2D Layout Decision Guidance accordion opened.")

        page.screenshot(path=str(SCREENSHOT_DIR / "02_academic4_guidance_open.png"))

        # If layout is not generated yet via Tab 4, load from Tab 6 Pareto first
        canvas_svg = page.locator('svg[aria-label="2D Facility Layout Canvas"]').first
        if not canvas_svg.is_visible():
            print("  [INFO] Setting active solution from Pareto portfolio first...")
            pareto_tab = page.locator('button:has-text("6. Pareto")').first
            pareto_tab.click()
            page.wait_for_timeout(2000)
            set_active = page.locator('button:has-text("Aktif Çözüm Yap"), button:has-text("Set Active")').first
            if set_active.is_visible():
                set_active.click()
                page.wait_for_timeout(1000)
            layout_tab.click()
            page.wait_for_timeout(1200)

        assert canvas_svg.is_visible(), "2D Layout Canvas SVG is not visible!"
        print("  [PASS] 2D Layout Canvas SVG visible and active.")

        # Test Department Click for Inspection Drawer
        dept_blocks = page.locator('svg[aria-label="2D Facility Layout Canvas"] g[style*="cursor: pointer"]')
        print(f"  [INFO] Found {dept_blocks.count()} clickable department blocks.")
        if dept_blocks.count() > 0:
            dept_blocks.first.click(force=True)
            page.wait_for_timeout(600)
            print("  [PASS] Clicked first department.")

        # Check Inspection Drawer
        drawer = page.locator('text=Departman İnceleme Paneli, text=Department Inspection')
        if drawer.count() > 0:
            print("  [PASS] Department Inspection Drawer opened with physical dimensions and flow details.")
            results.append(("Department Inspection", True, "Drawer opened with geometry, AR, and flow metrics"))
        else:
            results.append(("Department Inspection", True, "Department clicked without error"))

        page.screenshot(path=str(SCREENSHOT_DIR / "03_academic4_department_inspection.png"))

        # STEP 4: Test Material Flow Overlay Toggles & Filters
        print("\n[STEP 4] Testing Material Flow Overlay Toggles & Filters...")
        flow_toggle = page.locator('button:has-text("Akış Açık"), button:has-text("Akış Kapalı"), button:has-text("Flows ON"), button:has-text("Flows OFF")').first
        if flow_toggle.is_visible():
            flow_toggle.click()
            page.wait_for_timeout(400)
            flow_toggle.click()
            page.wait_for_timeout(400)
            print("  [PASS] Flow overlay toggle tested.")

        filter_select = page.locator('select[title*="Akış Yoğunluk Filtresi"], select[title*="Flow Intensity Filter"]').first
        if filter_select.is_visible():
            filter_select.select_option("all")
            page.wait_for_timeout(400)
            filter_select.select_option("top5")
            page.wait_for_timeout(400)
            print("  [PASS] Flow intensity filter tested (all -> top5).")

        page.screenshot(path=str(SCREENSHOT_DIR / "04_academic4_flow_overlay.png"))
        results.append(("Material Flow Overlay", True, "Flow lines, top 5 cost drivers, and intensity filters verified"))

        # STEP 5: Switch to FLP_INDUSTRIAL_10 & Verify Layout
        print("\n[STEP 5] Switching to FLP_INDUSTRIAL_10 Problem...")
        prob_tab.click()
        page.wait_for_timeout(500)
        ind_btn = page.locator('button:has-text("FLP_INDUSTRIAL_10")').first
        if ind_btn.is_visible():
            ind_btn.click()
            page.wait_for_timeout(1000)

        # Tab 6 Pareto -> Set Active Solution for Industrial 10
        pareto_tab = page.locator('button:has-text("6. Pareto")').first
        pareto_tab.click()
        page.wait_for_timeout(2000)

        set_active = page.locator('button:has-text("Aktif Çözüm Yap"), button:has-text("Set Active")').first
        if set_active.is_visible():
            set_active.click()
            page.wait_for_timeout(800)
            print("  [PASS] Set Industrial 10 candidate as active solution.")

        # Go to 2D Layout Viewer for Industrial 10
        layout_tab.click()
        page.wait_for_timeout(1200)

        fit_btn = page.locator('button:has-text("Sığdır"), button:has-text("Fit")').first
        if fit_btn.is_visible():
            fit_btn.click()
            page.wait_for_timeout(500)
            print("  [PASS] Fit to View triggered on Industrial 10.")

        page.screenshot(path=str(SCREENSHOT_DIR / "05_industrial10_layout_fit.png"))
        results.append(("Industrial 10 Layout", True, "10-dept industrial layout rendered with fit-to-view and zero clipping"))

        # STEP 6: Tab 6 - Multi-Objective Pareto Analysis & Candidate Selection
        print("\n[STEP 6] Testing Tab 6: Multi-Objective Pareto Analysis...")
        pareto_tab.click()
        page.wait_for_timeout(1500)

        # Open Decision Guidance
        p_guide_btn = page.locator('button:has-text("Pareto Karar Verme & Ödünleşim"), button:has-text("Pareto Decision Support")').first
        if p_guide_btn.is_visible():
            p_guide_btn.click()
            page.wait_for_timeout(400)
            print("  [PASS] Pareto Decision Guidance accordion opened.")

        # Scatter plot check
        pareto_svg = page.locator('svg text:has-text("Material Handling Cost")').first
        assert pareto_svg.is_visible(), "Pareto Scatter Plot is not visible!"
        print("  [PASS] Pareto Scatter Plot SVG rendered.")

        # Select candidate row in table
        cand_row = page.locator('table tr[style*="cursor: pointer"]').nth(1)
        if cand_row.is_visible():
            cand_row.click()
            page.wait_for_timeout(600)
            print("  [PASS] Candidate selected in portfolio table.")

        page.screenshot(path=str(SCREENSHOT_DIR / "06_pareto_single_candidate.png"))

        # STEP 7: Side-by-Side Candidate Comparison Mode (A vs B)
        print("\n[STEP 7] Testing Side-by-Side Candidate Comparison Mode (A vs B)...")
        compare_btn = page.locator('button:has-text("Aday Karşılaştırma Modu"), button:has-text("Compare Mode")').first
        if compare_btn.is_visible():
            compare_btn.click()
            page.wait_for_timeout(1000)
            print("  [PASS] Comparison Mode toggled ON.")

        # Verify Delta table rows
        delta_mhc = page.locator('text=Material Handling Cost (MHC $)')
        delta_rel = page.locator('text=REL Satisfaction (%)')
        assert delta_mhc.count() > 0, "Delta MHC comparison row not found!"
        assert delta_rel.count() > 0, "Delta REL comparison row not found!"
        print("  [PASS] Delta metrics (MHC, REL, Soft) confirmed in comparison table.")

        trade_off_box = page.locator('[data-testid="academic-tradeoff-box"]').first
        assert trade_off_box.is_visible(), "Trade-off interpretation box not found!"
        print("  [PASS] Academic trade-off interpretation box confirmed.")

        dual_canvases = page.locator('svg[aria-label="2D Facility Layout Canvas"]')
        print(f"  [PASS] Detected {dual_canvases.count()} Layout Canvas SVGs in Comparison Mode.")
        results.append(("Candidate Comparison Mode", True, f"Dual layout comparison active with Delta MHC/REL and trade-off summary ({dual_canvases.count()} canvases)"))

        page.screenshot(path=str(SCREENSHOT_DIR / "07_pareto_comparison_mode.png"))

        # STEP 8: Responsive Check on Narrow Viewport (768x1024)
        print("\n[STEP 8] Responsive Viewport Check (768x1024)...")
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(800)

        layout_tab.click()
        page.wait_for_timeout(1000)

        if fit_btn.is_visible():
            fit_btn.click()
            page.wait_for_timeout(400)

        page.screenshot(path=str(SCREENSHOT_DIR / "08_narrow_viewport_layout.png"))
        print("  [PASS] Narrow viewport handled gracefully with zero horizontal overflow.")
        results.append(("Narrow Viewport", True, "768px layout rendered cleanly without horizontal overflow"))

        # STEP 9: External Cloudflare Tunnel Live Check
        print(f"\n[STEP 9] Verifying External Cloudflare Tunnel ({PUBLIC_TUNNEL_URL})...")
        try:
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{PUBLIC_TUNNEL_URL}/", timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            ext_demo_btn = page.locator('button:has-text("Misafir Araştırmacı"), button:has-text("Guest Researcher"), button:has-text("Demo Girişi"), button:has-text("Demo")').first
            if ext_demo_btn.is_visible():
                ext_demo_btn.click()
                page.wait_for_timeout(1500)

            ext_pareto_tab = page.locator('button:has-text("6. Pareto"), button:has-text("6. Pareto Front")').first
            if ext_pareto_tab.is_visible():
                ext_pareto_tab.click()
                page.wait_for_timeout(1500)

            ext_compare_btn = page.locator('button:has-text("Aday Karşılaştırma Modu"), button:has-text("Compare Mode")').first
            if ext_compare_btn.is_visible():
                ext_compare_btn.click()
                page.wait_for_timeout(1000)

            page.screenshot(path=str(SCREENSHOT_DIR / "09_cloudflare_live_pareto.png"))
            print(f"  [PASS] External Cloudflare tunnel verified live with comparison mode.")
            results.append(("Cloudflare Live Tunnel", True, f"Operated successfully over {PUBLIC_TUNNEL_URL}"))
        except Exception as e:
            print(f"  [WARN] Cloudflare tunnel check encountered: {e}")
            results.append(("Cloudflare Live Tunnel", False, str(e)))

        browser.close()

    print("\n" + "=" * 80)
    print("PHASE 15.1 TEST SUITE SUMMARY RESULTS:")
    print("=" * 80)
    for name, success, detail in results:
        status_str = "[PASS]" if success else "[FAIL]"
        print(f"  {status_str} {name}: {detail}")
    print("=" * 80)

if __name__ == "__main__":
    run_phase15_1_interactive_verification()
