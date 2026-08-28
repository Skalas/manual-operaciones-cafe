"""Genera docs/stylesheets/brand.css con el color de acento de la marca activa.

La marca se elige con la variable de entorno BRAND (por defecto 'aluxe') y sus
colores salen de brands/<BRAND>.yml. Este archivo se regenera en cada build
(local y en build_all.py) y NO se versiona.

Uso:  BRAND=aluxe python scripts/gen_brand_css.py
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BRAND = os.environ.get("BRAND", "aluxe")
data = yaml.safe_load((ROOT / "brands" / f"{BRAND}.yml").read_text(encoding="utf-8"))

missing = [k for k in ("accent", "accent_light") if not data.get(k)]
if missing:
    raise SystemExit(
        f"brands/{BRAND}.yml no define {', '.join(missing)}. "
        "Cada marca debe declarar 'accent' y 'accent_light' (hex)."
    )
accent = data["accent"]
accent_light = data["accent_light"]
# 'chrome' (barra superior/navegación) y 'bg' (fondo de página) son opcionales;
# si faltan, el chrome cae al acento y el fondo queda en el de Material.
chrome = data.get("chrome", accent)
bg = data.get("bg")

bg_line = f"\n  --md-default-bg-color: {bg};" if bg else ""

css = f"""/* Generado por scripts/gen_brand_css.py — no editar a mano. Marca: {BRAND}. */
/* Modo claro bajo [data-md-color-scheme="default"] para ganar en especificidad
   a las variables de paleta de Material (un :root no las sobreescribe). */
[data-md-color-scheme="default"] {{
  --md-primary-fg-color: {chrome};
  --md-primary-fg-color--light: {chrome};
  --md-primary-fg-color--dark: {chrome};
  --md-accent-fg-color: {accent};
  --md-typeset-a-color: {accent};
  --brand-accent: {accent};
  --brand-accent-strong: {accent};{bg_line}
}}
[data-md-color-scheme="slate"] {{
  --md-primary-fg-color: {chrome};
  --md-accent-fg-color: {accent_light};
  --md-typeset-a-color: {accent_light};
  --brand-accent: {accent_light};
}}
"""

out = ROOT / "docs" / "stylesheets" / "brand.css"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(css, encoding="utf-8")
print(f"docs/stylesheets/brand.css ({BRAND}: {accent})")
