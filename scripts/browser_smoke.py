"""Exercise the running demo UI. Start the app separately on port 3000."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from playwright.sync_api import sync_playwright, expect


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "artifacts" / "browser"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    failed_requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: failed_requests.append(f"{response.status} {response.url}") if response.status >= 400 else None)
        page.goto(os.environ.get("PYREXIA_URL", "http://127.0.0.1:3000"), wait_until="networkidle")
        page.get_by_role("button", name="Run guided demo", exact=True).click()
        expect(page.locator("#notice")).to_contain_text("Experiment complete", timeout=30_000)
        expect(page.locator("#plot-source-badge")).to_have_text("Synthetic data")
        page.wait_for_function("Boolean(document.querySelector('#activity-chart .plot-container'))")
        page.screenshot(path=str(output / "studio-desktop.png"), full_page=True)
        page.locator('.nav-button[data-page="intelligence"]').click()
        expect(page.locator("#analysis-result .metric-card")).not_to_have_count(0)
        page.locator("#braindance-analyze").click()
        expect(page.locator("#braindance-result")).to_be_visible()
        expect(page.locator("#braindance-result")).to_contain_text("source reward units")
        page.screenshot(path=str(output / "intelligence-desktop.png"), full_page=True)
        page.locator('.nav-button[data-page="evidence"]').click()
        page.locator("[data-verify]").first.click()
        expect(page.locator("#verify-result")).to_contain_text("Verification passed", timeout=30_000)
        with page.expect_download() as download:
            page.locator('#evidence-table a[href$="/evidence"]').first.click()
        evidence = output / "synthetic-evidence.zip"
        download.value.save_as(evidence)
        verification = subprocess.run([sys.executable, str(root / "scripts" / "verify_evidence.py"), str(evidence)], check=True, text=True, capture_output=True)
        page.locator('.nav-button[data-page="studio"]').click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile page overflows horizontally"
        page.screenshot(path=str(output / "studio-mobile.png"), full_page=True)
        browser.close()
    assert not errors, errors
    assert not failed_requests, failed_requests
    result = {"passed": True, "browser_errors": errors, "failed_requests": failed_requests, "evidence_verification": json.loads(verification.stdout), "screenshots": str(output)}
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
