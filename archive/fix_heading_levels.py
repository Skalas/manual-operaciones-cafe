"""Corrige la jerarquía de encabezados en docs/*.md (migración de una sola vez).

El documento original usaba '#' (H1) para casi todo, así que cada página tenía
muchos H1 y no había jerarquía visual. Este script deja UN solo H1 por página
(el título) y baja un nivel todos los encabezados siguientes, preservando la
anidación relativa del autor.

Es idempotente: si una página ya tiene exactamente un H1, se omite.

Uso:  python scripts/fix_heading_levels.py
"""

from __future__ import annotations

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
HEADING = re.compile(r"^(#{1,6})(\s)")


def fix(md: str) -> str | None:
    if sum(1 for ln in md.split("\n") if ln.startswith("# ")) <= 1:
        return None  # ya está bien
    out, seen_first = [], False
    for ln in md.split("\n"):
        m = HEADING.match(ln)
        if m:
            if not seen_first:
                seen_first = True
            elif len(m.group(1)) < 6:
                ln = "#" + ln
        out.append(ln)
    return "\n".join(out)


def main() -> None:
    changed = 0
    for path in sorted(DOCS.glob("*.md")):
        fixed = fix(path.read_text(encoding="utf-8"))
        if fixed is not None:
            path.write_text(fixed, encoding="utf-8")
            changed += 1
            print(f"  corregido: {path.name}")
    print(f"\n{changed} página(s) corregida(s).")


if __name__ == "__main__":
    main()
