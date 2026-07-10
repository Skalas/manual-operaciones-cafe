"""Genera docs/stylesheets/brand.css con el color de acento de la marca activa.

La marca se elige con la variable de entorno BRAND (por defecto 'brown') y sus
colores salen de brands/<BRAND>.yml. Este archivo se regenera en cada build
(local y en build_all.py) y NO se versiona.

Uso:  BRAND=aluxe python scripts/gen_brand_css.py
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BRAND = os.environ.get("BRAND", "brown")
data = yaml.safe_load((ROOT / "brands" / f"{BRAND}.yml").read_text(encoding="utf-8"))

accent = data.get("accent", "#92400E")
accent_light = data.get("accent_light", "#C2691C")

css = f"""/* Generado por scripts/gen_brand_css.py — no editar a mano. Marca: {BRAND}. */
:root {{
  --md-primary-fg-color: {accent};
  --md-primary-fg-color--light: {accent_light};
  --md-primary-fg-color--dark: {accent};
  --md-accent-fg-color: {accent_light};
  --brand-accent: {accent};
  --brand-accent-strong: {accent};
}}
[data-md-color-scheme="slate"] {{
  --md-primary-fg-color: {accent_light};
  --md-accent-fg-color: {accent_light};
  --brand-accent: {accent_light};
}}
"""

out = ROOT / "docs" / "stylesheets" / "brand.css"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(css, encoding="utf-8")
print(f"docs/stylesheets/brand.css ({BRAND}: {accent})")
