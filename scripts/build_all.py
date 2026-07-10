"""Construye un sitio por marca desde una sola fuente.

Para cada archivo brands/<marca>.yml:
  1. Regenera los PDFs de formatos con la marca correspondiente.
  2. Ejecuta `mkdocs build` en site/<marca>/ con SITE_NAME y SITE_URL de esa marca.
Luego escribe site/index.html: una portada que enlaza a todas las marcas.

Uso:   python scripts/build_all.py
Config: BASE_URL define la URL pública base (por defecto, GitHub Pages del repo).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BRANDS_DIR = ROOT / "brands"
SITE = ROOT / "site"
BASE_URL = os.environ.get("BASE_URL", "https://skalas.github.io/manual-operaciones-cafe").rstrip("/")
PY = sys.executable


def build_brand(brand_id: str, data: dict) -> None:
    site_dir = SITE / brand_id
    env = {
        **os.environ,
        "BRAND": brand_id,
        "SITE_NAME": f"Manual de Operación — {data['name']}",
        "SITE_URL": f"{BASE_URL}/{brand_id}/",
    }
    print(f"\n=== {data['name']} ({brand_id}) ===")
    subprocess.run([PY, "scripts/gen_brand_css.py"], cwd=ROOT, env=env, check=True)
    subprocess.run([PY, "scripts/build_formatos_pdf.py"], cwd=ROOT, env=env, check=True)
    subprocess.run(
        [PY, "-m", "mkdocs", "build", "--strict", "-d", str(site_dir)],
        cwd=ROOT, env=env, check=True,
    )


def write_landing(brands: list[tuple[str, dict]]) -> None:
    cards = "\n".join(
        f'      <a class="card" href="{bid}/">'
        f'<span class="name">{d["name"]}</span>'
        f'<span class="go">Abrir manual →</span></a>'
        for bid, d in brands
    )
    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manuales de Operación</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f3f0; color: #2b2320; padding: 2rem; }}
  @media (prefers-color-scheme: dark) {{ body {{ background: #1a1614; color: #ece6e1; }} }}
  main {{ width: 100%; max-width: 640px; text-align: center; }}
  h1 {{ font-weight: 700; font-size: 1.6rem; margin: 0 0 .4rem; }}
  p.sub {{ margin: 0 0 2rem; opacity: .7; }}
  .cards {{ display: grid; gap: 1rem; }}
  .card {{ display: flex; justify-content: space-between; align-items: center;
    padding: 1.25rem 1.5rem; border-radius: 14px; text-decoration: none;
    background: #fff; color: inherit; box-shadow: 0 1px 3px rgba(0,0,0,.12);
    transition: transform .12s ease, box-shadow .12s ease; }}
  @media (prefers-color-scheme: dark) {{ .card {{ background: #262019; }} }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,.18); }}
  .name {{ font-weight: 600; font-size: 1.15rem; }}
  .go {{ opacity: .6; font-size: .9rem; }}
</style>
</head>
<body>
  <main>
    <h1>Manuales de Operación</h1>
    <p class="sub">Selecciona una marca</p>
    <div class="cards">
{cards}
    </div>
  </main>
</body>
</html>
"""
    (SITE / "index.html").write_text(html, encoding="utf-8")
    print(f"\nPortada: site/index.html ({len(brands)} marcas)")


def main() -> None:
    brands = sorted((p.stem, yaml.safe_load(p.read_text(encoding="utf-8")))
                    for p in BRANDS_DIR.glob("*.yml"))
    if not brands:
        raise SystemExit("No hay marcas en brands/*.yml")
    for bid, data in brands:
        build_brand(bid, data)
    write_landing(brands)
    print(f"\nListo. Sitio combinado en: {SITE}")


if __name__ == "__main__":
    main()
