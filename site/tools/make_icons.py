"""Génère les icônes PNG de l'application (192, 512 et 180 px pour iOS) avec Chromium (Playwright, .venv)."""
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "icons"
SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#1A3A6B"/>
  <text x="256" y="330" text-anchor="middle" font-family="Georgia, serif" font-weight="700" font-size="300" fill="#F8F6F1">V</text>
  <rect x="96" y="390" width="320" height="18" fill="#F8F6F1" opacity=".55"/>
</svg>"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "icon.svg").write_text(SVG, "utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size in (192, 512, 180):
            page = browser.new_page(viewport={"width": size, "height": size})
            page.set_content(f"<style>html,body{{margin:0}}svg{{width:{size}px;height:{size}px;display:block}}</style>{SVG}")
            page.screenshot(path=str(OUT / f"icon-{size}.png"))
            page.close()
        browser.close()
    print("icônes écrites dans", OUT)


if __name__ == "__main__":
    main()
