"""Módulo de macros para MkDocs (mkdocs-macros-plugin).

Carga la configuración de marca seleccionada por la variable de entorno BRAND
(por defecto 'brown') desde brands/<BRAND>.yml y la expone en las páginas como
`brand.name`, `brand.short`, `brand.code`.

Uso en Markdown:  {{ brand.name }}, {{ brand.short }}, {{ brand.code }}
Build por marca:  BRAND=aluxe mkdocs build
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

BRANDS_DIR = Path(__file__).resolve().parent / "brands"


def define_env(env) -> None:
    brand_id = os.environ.get("BRAND", "brown")
    brand_file = BRANDS_DIR / f"{brand_id}.yml"
    if not brand_file.exists():
        raise FileNotFoundError(
            f"No existe la configuración de marca: {brand_file}. "
            f"Marcas disponibles: {[p.stem for p in BRANDS_DIR.glob('*.yml')]}"
        )
    env.variables["brand"] = yaml.safe_load(brand_file.read_text(encoding="utf-8"))
