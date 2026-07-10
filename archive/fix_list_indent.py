"""Normaliza la sangría de sublistas en docs/*.md a 4 espacios.

El documento original indentaba las sublistas con 3 espacios. python-markdown
(motor de MkDocs) exige 4 espacios para anidar; con 3 no anida y, bajo una lista
numerada, renumera las viñetas (1, 2, 3…) en vez de mostrarlas anidadas.

Reindenta a 4 espacios los ítems de lista con 3 espacios iniciales.
Idempotente: una línea ya con 4 espacios no vuelve a coincidir.

Uso:  python scripts/fix_list_indent.py
"""

from __future__ import annotations

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
LIST_ITEM_3SP = re.compile(r"^ {3}([*+\-]|\d+\.)(\s)")


def fix(md: str) -> str | None:
    lines = md.split("\n")
    out, changed = [], False
    for ln in lines:
        if LIST_ITEM_3SP.match(ln):
            ln = " " + ln  # 3 -> 4 espacios
            changed = True
        out.append(ln)
    return "\n".join(out) if changed else None


def main() -> None:
    n = 0
    for path in sorted(DOCS.glob("*.md")):
        fixed = fix(path.read_text(encoding="utf-8"))
        if fixed is not None:
            path.write_text(fixed, encoding="utf-8")
            n += 1
            print(f"  corregido: {path.name}")
    print(f"\n{n} página(s) corregida(s).")


if __name__ == "__main__":
    main()
