"""Vérification de bout en bout du site (Chromium sans fenêtre) : pages principales, recherche, suivis, mobile.

Usage : servir `site/` sur http://127.0.0.1:8934 puis `.venv/Scripts/python site/tests/e2e_smoke.py`.
Outil de vérification local (Playwright dans .venv), hors des dépendances du pipeline.
"""
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8934/"
errors, checks = [], []


def check(name: str, ok: bool) -> None:
    checks.append((name, ok))
    print(("OK   " if ok else "ÉCHEC"), name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    for label, viewport in (("bureau", {"width": 1280, "height": 900}), ("mobile", {"width": 390, "height": 844})):
        page = browser.new_page(viewport=viewport)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(BASE + "?reset#/")
        page.wait_for_selector(".block")
        check(f"{label} : Accueil avec {page.locator('.block').count()} veilles", page.locator(".block").count() >= 9)
        check(f"{label} : pas de défilement horizontal", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        for d in ("football", "finance", "f1", "nba", "tennis"):
            page.goto(BASE + f"#/d/{d}")
            page.wait_for_selector("h1")
            check(f"{label} : page {d} affichée", page.locator("h1").inner_text().strip() != "")
        page.goto(BASE + "#/s/")
        page.wait_for_selector("#q")
        page.fill("#q", "")
        total = page.locator("#results a.row").count()
        page.fill("#q", "zzzzqqq")
        check(f"{label} : recherche vide → archives ({total} résultats)", total > 0)
        check(f"{label} : recherche sans résultat gérée", "Aucun résultat" in page.locator("#results").inner_text())
        page.goto(BASE + "#/")
        page.wait_for_selector(".card")
        page.locator(".card").first.click()
        page.wait_for_selector("article.detail")
        chips = page.locator("button.chip")
        if chips.count():
            entity = chips.first.get_attribute("data-entity")
            chips.first.click()
            check(f"{label} : suivre « {entity} »", chips.first.get_attribute("aria-pressed") == "true")
            page.goto(BASE + "#/")
            page.wait_for_selector(".block")
            check(f"{label} : section « Vos suivis » sur l'Accueil", page.locator("text=Vos suivis").count() == 1)
        page.keyboard.press("Control+k")
        page.wait_for_selector("#q")
        check(f"{label} : Ctrl+K ouvre la recherche", "#/s/" in page.url)
        page.close()
    browser.close()

print("\nErreurs console :", errors or "aucune")
sys.exit(0 if all(ok for _, ok in checks) and not errors else 1)
