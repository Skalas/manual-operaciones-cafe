"""Divide el monolito 'Manual de Operación.md' en páginas para MkDocs.

Alcance: SOLO presentación. Se preserva el contenido verbatim (valores, tablas,
redacción de política). La limpieza se limita a artefactos del export de Google Docs:
encabezados vacíos usados como saltos de página, caracteres escapados (1\\. / \\_\\_),
`**` que envuelven encabezados y numeración de sección pegada al título (1.1Título).

Sin dependencias externas: solo biblioteca estándar. Reproducible.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Manual de Operación.md"
OUT = ROOT / "docs"

# Marcador de inicio de sección de contenido: captura "1.1", "2.3" o "Anexo A".
MARKER = re.compile(r"^#*\s*\*\*((?:\d\.\d)|(?:Anexo\s+[A-E]))\s*(.*?)\*\*\s*$")

# code -> (nombre de archivo)
CODE_TO_FILE = {
    "1.1": "cap1-marca",
    "1.2": "cap1-convivencia",
    "1.3": "cap1-no-discriminacion",
    "2.1": "cap2-conducta",
    "2.2": "cap2-faltas",
    "2.3": "cap2-investigacion",
    "2.4": "cap2-quejas",
    "2.5": "cap2-hostigamiento",
    "3.1": "cap3-seguridad-higiene",
    "3.2": "cap3-emergencias",
    "4.1": "cap4-calidad-cafe",
    "4.2": "cap4-inventarios",
    "4.3": "cap4-caja",
    "4.4": "cap4-consumo",
    "4.5": "cap4-redes",
    "5.1": "cap5-kpis",
    "Anexo A": "anexo-a",
    "Anexo B": "anexo-b",
    "Anexo C": "anexo-c",
    "Anexo D": "anexo-d",
    "Anexo E": "anexo-e",
}


def clean(text: str) -> str:
    """Limpia artefactos de formato sin tocar el contenido."""
    # 1) Quitar backslashes de escape del export (1\. -> 1.  ;  \_ -> _).
    text = re.sub(r"\\([._#()\-])", r"\1", text)

    out: list[str] = []
    prev_blank = False
    for ln in text.split("\n"):
        # 2) Eliminar encabezados vacíos (saltos de página de Google Docs).
        if re.match(r"^#{1,6}[ \t]*$", ln):
            continue
        # 3) Quitar ** que envuelven un encabezado completo: "# **X**" -> "# X".
        m = re.match(r"^(#{1,6})\s*\*\*(.*?)\*\*\s*$", ln)
        if m:
            ln = f"{m.group(1)} {m.group(2).strip()}"
        # 4) Colapsar líneas en blanco consecutivas.
        blank = ln.strip() == ""
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank

    return "\n".join(out).strip() + "\n"


def find(lines: list[str], needle: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if needle in lines[i]:
            return i
    raise ValueError(f"No encontrado: {needle!r}")


def write(name: str, body: str) -> None:
    (OUT / f"{name}.md").write_text(clean(body), encoding="utf-8")
    print(f"  docs/{name}.md")


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    OUT.mkdir(exist_ok=True)

    i_filosofia = find(lines, "**Filosofía de la empresa**")
    i_cap1_toc = find(lines, "**CAPÍTULO I**")
    # La versión de contenido de 1.1 no lleva espacio: "**1.1Manual...".
    i_content = find(lines, "**1.1Manual de Marca Operativa")

    print("Generando páginas:")

    # --- Front matter ---
    write("index", "\n".join(lines[:i_filosofia]))
    write("introduccion", "\n".join(lines[i_filosofia:i_cap1_toc]))

    # --- Secciones de contenido y anexos ---
    markers: list[tuple[int, str, str]] = []
    for i in range(i_content, len(lines)):
        m = MARKER.match(lines[i])
        if m:
            markers.append((i, m.group(1).strip(), m.group(2).strip()))

    for k, (idx, code, title) in enumerate(markers):
        end = markers[k + 1][0] if k + 1 < len(markers) else len(lines)
        body = "\n".join(lines[idx + 1 : end])
        heading = f"# {code} — {title}" if code.startswith("Anexo") else f"# {code} {title}"
        write(CODE_TO_FILE[code], f"{heading}\n\n{body}")

    print(f"\nTotal: {2 + len(markers)} páginas. Faltantes esperados: 0")
    missing = set(CODE_TO_FILE) - {c for _, c, _ in markers}
    if missing:
        print(f"ADVERTENCIA — secciones no encontradas: {sorted(missing)}")


if __name__ == "__main__":
    main()
