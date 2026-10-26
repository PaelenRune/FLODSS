"""Headless React interaction regression; no API, login or dev server required."""
from pathlib import Path
import os
import subprocess
from playwright.sync_api import sync_playwright, expect


def test_cockpit_what_if():
    frontend = Path(__file__).resolve().parents[1]
    bundle = frontend / 'node_modules/.cache/cockpit-interaction.js'
    subprocess.run([
        str(frontend / 'node_modules/.bin/esbuild.cmd'),
        'scripts/cockpit-interaction-fixture.tsx', '--bundle', '--format=iife',
        '--jsx=automatic', '--loader:.css=empty', f'--outfile={bundle}',
    ], cwd=frontend, check=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.environ.get('PLAYWRIGHT_CHANNEL'))
        try:
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_content('<div id="root"></div>')
            page.add_script_tag(path=str(bundle))
            page.wait_for_load_state('networkidle')
            rows = page.locator('.scenario-row')
            cost = page.locator('.cockpit-kpi').nth(3).locator('strong')
            expect(rows).to_have_count(1)
            expect(cost).to_have_text('400')
            page.locator('[data-department="A"]').click()
            original = page.locator('[data-department="A"] polygon').first.get_attribute('points')
            original_flow = page.locator('.factory-flow path').first.get_attribute('d')
            page.get_by_role('button', name='Swap with…', exact=True).click()
            page.locator('[data-department="B"]').focus()
            page.keyboard.press('Enter')
            expect(rows).to_have_count(2)
            expect(cost).to_have_text('200')
            expect(page.locator('.cockpit-kpi').nth(3)).to_contain_text('-50% vs Baseline')
            assert page.locator('[data-department="A"] polygon').first.get_attribute('points') != original
            assert page.locator('.factory-flow path').first.get_attribute('d') != original_flow
            rows.first.click()
            expect(cost).to_have_text('400')
            assert page.locator('[data-department="A"] polygon').first.get_attribute('points') == original
            assert page.locator('.factory-flow path').first.get_attribute('d') == original_flow
            rows.nth(1).click()
            expect(cost).to_have_text('200')
            page.get_by_role('button', name='Toggle cockpit', exact=True).click()
            page.get_by_role('button', name='Toggle cockpit', exact=True).click()
            expect(rows).to_have_count(2)
            expect(cost).to_have_text('200')
            page.get_by_role('button', name='Receive solver', exact=True).click()
            expect(rows).to_have_count(3)
            expect(rows.last).to_contain_text('Solver Layout')
            expect(cost).to_have_text('300')
            rows.first.click()
            expect(cost).to_have_text('400')
            page.get_by_role('button', name='Change problem', exact=True).click()
            expect(rows).to_have_count(0)
            expect(cost).to_have_text('0')
            assert not errors, errors
        finally:
            browser.close()


if __name__ == '__main__':
    test_cockpit_what_if()
    print('PASS: keyboard swap, instant KPI delta, scenario replay, navigation persistence, solver history and problem isolation')
