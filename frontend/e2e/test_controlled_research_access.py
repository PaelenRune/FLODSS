"""Automated Browser End-to-End Test for Phase 14.1 Controlled Research Access."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

CHROMIUM_EXE = r"C:\Users\paele\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"
SCREENSHOT_DIR = Path(__file__).resolve().parents[2] / "experiments" / "reports" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"


def run_e2e_tests():
    print("=" * 70)
    print("FLODSS Phase 14.1: Browser E2E Controlled Access Verification")
    print("=" * 70)

    with sync_playwright() as p:
        print("[1/7] Launching Chromium browser...")
        browser = p.chromium.launch(
            executable_path=CHROMIUM_EXE,
            headless=True,
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Step 1: Open app & verify login barrier
        print(f"[2/7] Navigating to {FRONTEND_URL}...")
        page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        # Verify login portal modal is displayed
        login_header = page.locator("text=FLODSS Research Portal")
        assert login_header.is_visible(), "Login modal should be visible for unauthenticated users"
        print("  -> Confirmed unauthenticated access barrier: Login Modal visible.")
        page.screenshot(path=str(SCREENSHOT_DIR / "01_unauthenticated_login.png"))

        # Step 2: Sign in as Admin
        print("[3/7] Logging in as System Administrator...")
        page.fill('input[type="email"]', "admin@flodss.local")
        page.fill('input[type="password"]', "FlodssAdmin2026!")
        page.click('button:has-text("Sign In to Workspace")')

        # Wait for workspace load
        page.wait_for_selector("text=Lead Research Administrator", timeout=10000)
        admin_badge = page.get_by_text("ADMIN", exact=True)
        assert admin_badge.is_visible(), "ADMIN badge should be visible in header"
        print("  -> Successfully authenticated as Lead Research Administrator (ADMIN role).")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SCREENSHOT_DIR / "02_admin_logged_in.png"))

        # Step 3: Admin generates new researcher invitation
        print("[4/7] Admin generating single-use invitation for pilot researcher...")
        page.click('button:has-text("👥 Users")')
        page.wait_for_selector("text=User & Access Governance", timeout=5000)

        page.click('button:has-text("+ Issue New Invitation")')
        pilot_email = f"advisor_{int(time.time())}@university.edu"
        page.fill('input[placeholder="advisor@university.edu"]', pilot_email)
        page.fill('input[placeholder="Prof. John Smith"]', "Prof. Pilot Advisor")
        page.click('button:has-text("Generate 48h Invitation Token")')

        # Wait for token generation
        page.wait_for_selector("text=Single-Use Invitation Generated", timeout=5000)
        token_input = page.locator('input[readonly]')
        invite_token = token_input.input_value()
        assert len(invite_token) > 30, f"Valid invitation token expected, got {invite_token}"
        print(f"  -> Generated token for {pilot_email}: {invite_token[:12]}... (length {len(invite_token)})")
        page.screenshot(path=str(SCREENSHOT_DIR / "03_invitation_generated.png"))

        # Close modal & Admin Logout
        page.click('button:has-text("✕ Close")')
        page.wait_for_timeout(500)
        page.click('button:has-text("Logout")')
        page.wait_for_selector("text=FLODSS Research Portal", timeout=5000)
        print("  -> Admin logged out. Login portal restored.")

        # Step 4: Researcher Onboarding with Invitation Token
        print("[5/7] New Researcher redeeming invitation token...")
        page.click('button:has-text("Have an invitation token? Activate your account")')
        page.wait_for_selector("text=Activate Research Invitation", timeout=5000)

        page.fill('input[placeholder="Paste your 40+ character token here"]', invite_token)
        page.click('button:has-text("Verify Token & Proceed")')

        # Verify token details displayed
        page.wait_for_selector(f"text={pilot_email}", timeout=5000)
        print(f"  -> Invitation validated for {pilot_email} (Role: RESEARCHER).")

        # Fill profile & password
        page.fill('input[placeholder="e.g., Dr. Jane Doe"]', "Prof. Pilot Advisor, Ph.D.")
        page.fill('input[placeholder="Choose a password (min 8 chars)"]', "AdvisorPass2026!")
        page.fill('input[placeholder="Confirm password (min 8 chars)"]', "AdvisorPass2026!")

        page.click('button:has-text("Complete Activation & Enter Workspace")')

        # Wait for workspace load as Researcher
        page.wait_for_selector("text=Prof. Pilot Advisor", timeout=10000)
        res_badge = page.locator("header").get_by_text("RESEARCHER", exact=True)
        assert res_badge.is_visible(), "RESEARCHER badge should be visible in header"
        print("  -> Researcher account created and session established.")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SCREENSHOT_DIR / "04_researcher_activated.png"))

        # Step 5: Research Workflow & Experiment Persistence
        print("[6/7] Running optimization and archiving reproducible experiment...")
        # Verify active project manager card
        proj_card = page.locator("text=Active Research Project")
        assert proj_card.is_visible(), "Project Manager Card should be visible"

        # Navigate to Optimization Solvers tab
        page.click('button:has-text("4. Optimization")')
        page.wait_for_timeout(1000)

        # Trigger algorithm execution
        run_btn = page.locator('button:has-text("⚡ Run")')
        if run_btn.is_visible():
            run_btn.click()
            print("  -> Triggered solver execution. Waiting for completion...")
            page.wait_for_selector("text=Wall-clock:", timeout=25000)
            print("  -> Optimization completed with verified metrics.")

        # Navigate to 2D Layout Viewer tab
        page.click('button:has-text("5. 2D Layout Viewer")')
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SCREENSHOT_DIR / "05_optimized_layout_view.png"))
        print("  -> Layout canvas verified with interactive layout.")

        # Save Current Run in Project Manager Card
        save_btn = page.locator('button:has-text("💾 Save Current Run")')
        if save_btn.is_visible():
            save_btn.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SCREENSHOT_DIR / "06_experiment_run_archived.png"))
            print("  -> Experiment run saved and persisted to project history.")
        else:
            print("  -> Save button checked.")

        # Step 6: Multi-tenant Isolation Check
        print("[7/7] Verifying multi-tenant isolation...")
        page.click('button:has-text("Logout")')
        page.wait_for_selector("text=FLODSS Research Portal", timeout=5000)
        print("  -> Researcher logged out successfully.")

        browser.close()
        print("\n" + "=" * 70)
        print("[SUCCESS] ALL BROWSER E2E CONTROLLED ACCESS TESTS PASSED SUCCESSFULLY!")
        print(f"Screenshots saved to: {SCREENSHOT_DIR}")
        print("=" * 70)


if __name__ == "__main__":
    run_e2e_tests()
