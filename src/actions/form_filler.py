# src/pasa/actions/form_filler.py
from playwright.sync_api import sync_playwright

def fill_google_form(form_url, field_map: dict):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(form_url)
        for label, value in field_map.items():
            # Locate fields by visible label
            page.get_by_label(label).fill(value)
        page.click('button[type="submit"]')
        browser.close()
