"""Vérification de bout en bout du site Vigie 2 (Chromium sans fenêtre) : pages, pastilles, panneau, recherche, thème, hors ligne.

Usage : servir `site/` sur http://127.0.0.1:8934 puis `.venv/Scripts/python site/tests/e2e_smoke.py [URL]`.
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


def settle(page) -> None:
    page.wait_for_timeout(900)
    page.evaluate("document.querySelectorAll('.card,.data').forEach((e) => e.classList.add('in'))")


with sync_playwright() as p:
    browser = p.chromium.launch()
    for label, viewport in (("bureau", {"width": 1280, "height": 900}), ("mobile", {"width": 390, "height": 844})):
        page = browser.new_page(viewport=viewport)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(BASE + "?reset#/")
        page.wait_for_selector(".uband")
        settle(page)
        check(f"{label} : Accueil avec {page.locator('.uband').count()} univers", page.locator(".uband").count() == 4)
        check(f"{label} : {page.locator('main .card').count()} cartes illustrées", page.locator("main .card").count() >= 8
              and page.locator("main .card .visual svg").count() == page.locator("main .card").count())
        check(f"{label} : bandeau rempli", page.locator("#band .bi").count() > 0)
        check(f"{label} : pas de défilement horizontal", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        for u in ("finance", "ia", "geopolitique", "sport"):
            page.goto(BASE + f"#/u/{u}")
            page.wait_for_selector(".universe")
            check(f"{label} : univers {u}", page.locator(".universe .tabs a").count() >= 2)
        page.goto(BASE + "#/u/sport/foot")
        try:   # la page Sport précédente a déjà un .universe : on attend l'onglet actif du nouveau rendu
            page.wait_for_function("document.querySelector('.tabs a[aria-current=\"page\"]')?.textContent.trim() === 'Football'", timeout=5000)
            foot_ok = True
        except Exception:
            foot_ok = False
        check(f"{label} : sous-thème football actif", foot_ok)
        page.goto(BASE + "#/d/football/mercato")
        page.wait_for_selector(".universe")
        check(f"{label} : ancienne adresse redirigée", "#/u/sport/foot" in page.url)
        page.goto(BASE + "#/")
        page.wait_for_selector(".uband")
        settle(page)
        page.locator("main a.stretch").first.click()
        page.wait_for_selector("article.event")
        check(f"{label} : page événement", page.locator("article.event h1").count() == 1)
        page.goto(BASE + "#/")
        page.wait_for_selector(".uband")
        settle(page)
        pill = page.locator("main .pill").first
        name = pill.inner_text().strip()
        pill.click()
        page.wait_for_selector("#panel .pactions")
        check(f"{label} : panneau d’aperçu de « {name} »", page.locator("#panel h2").inner_text().strip() == name)
        for _ in range(20):
            page.keyboard.press("Tab")
        check(f"{label} : le focus reste dans le panneau", page.evaluate("document.getElementById('panel').contains(document.activeElement)"))
        page.locator("#panel [data-action=follow]").click()
        check(f"{label} : suivre depuis le panneau", page.locator("#panel [data-action=follow]").get_attribute("aria-pressed") == "true")
        if label == "bureau":
            page.wait_for_timeout(1500)
            check(f"{label} : le Radar montre les actualités du premier suivi", page.locator("#radar .plist li").count() > 0)
        page.locator("#panel a.btn.primary").click()
        page.wait_for_selector("article.entity")
        check(f"{label} : fiche entité ouverte", page.locator("article.entity h1").inner_text().strip() == name)
        page.keyboard.press("Control+k")
        page.wait_for_selector("#q")
        page.fill("#q", "nvidia")
        page.wait_for_timeout(600)
        check(f"{label} : recherche d’entité", page.locator('#results [data-entity="company:nvidia"]').count() == 1)
        check(f"{label} : résultats visibles pendant la frappe",
              page.evaluate("getComputedStyle(document.querySelector('#results .data')).opacity") == "1")
        page.goto(BASE + "#/")
        page.wait_for_selector(".uband")
        page.locator("details.settings summary").click()
        page.locator('[data-action="move"][data-universe="ia"][data-dir="-1"]').scroll_into_view_if_needed()
        before = page.evaluate("scrollY")
        page.locator('[data-action="move"][data-universe="ia"][data-dir="-1"]').click()
        page.wait_for_timeout(500)
        order = page.evaluate("[...document.querySelectorAll('.uband')].map((s) => s.className.split('u-')[1])")
        check(f"{label} : réordonner garde la place, les réglages ouverts et le focus",
              order[0] == "ia" and page.evaluate("scrollY") > before - 200 and before > 200
              and page.evaluate("document.querySelector('details.settings').open")
              and page.evaluate("document.activeElement?.dataset?.universe") == "ia")
        page.goto(BASE + "#/")
        page.wait_for_selector(".uband")
        page.locator('[data-action="theme-cycle"]').click()
        check(f"{label} : thème forcé", page.evaluate("document.documentElement.dataset.theme") == "dark")
        page.close()
    # Application installable et lecture hors ligne (service worker, réseau d'abord, cache en secours)
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + "#/")
    page.wait_for_selector(".uband")
    check("service worker actif", page.evaluate(
        "Promise.race([navigator.serviceWorker.ready.then(() => true), new Promise((r) => setTimeout(() => r(false), 5000))])"))
    page.reload()
    page.wait_for_selector(".uband")
    context.set_offline(True)
    try:
        page.reload(timeout=10000)
        page.wait_for_selector(".uband", timeout=10000)
        offline_ok = page.locator(".uband").count() == 4
    except Exception:
        offline_ok = False
    check("hors ligne : l’Accueil s’affiche depuis le cache", offline_ok)
    context.set_offline(False)
    context.close()
    browser.close()

print("\nErreurs console :", errors or "aucune")
sys.exit(0 if all(ok for _, ok in checks) and not errors else 1)
