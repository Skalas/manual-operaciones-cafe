"""Genera PDFs imprimibles del manual con pandoc + xelatex, por marca.

Salida (local, no se publica en el sitio):
    pdf/manual-completo-<marca>.pdf
    pdf/referencia-rapida-<marca>.pdf

- Toma el contenido de docs/ (fuente única).
- Resuelve la marca ({{ brand.* }}) desde brands/<marca>.yml.
- Cada archivo de docs/ se convierte en un capítulo; sus encabezados internos
  bajan un nivel para una jerarquía e índice limpios.
- Portada, índice, numeración de página y pie "documento controlado".

Uso:  python scripts/build_manual_pdf.py
Requiere pandoc y xelatex en el PATH.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "pdf"
BRANDS_DIR = ROOT / "brands"

# Orden completo (mismo del menú del sitio).
FULL = [
    "index", "introduccion",
    "cap1-marca", "cap1-convivencia", "cap1-no-discriminacion",
    "cap2-conducta", "cap2-faltas", "cap2-investigacion", "cap2-quejas", "cap2-hostigamiento",
    "cap3-seguridad-higiene", "cap3-emergencias", "cap3-videovigilancia",
    "cap4-calidad-cafe", "cap4-inventarios", "cap4-caja", "cap4-consumo", "cap4-redes",
    "cap5-kpis",
    "anexo-a", "anexo-b", "anexo-c", "anexo-d", "anexo-e",
    "formatos",
]

# Referencia rápida: solo lo que vale la pena tener a la mano en barra.
QUICK = [
    "cap4-calidad-cafe",       # parámetros de espresso, leche, agua, calibración
    "cap3-seguridad-higiene",  # reglas de seguridad e higiene
    "cap3-emergencias",        # protocolos de emergencia
    "anexo-c",                 # seguridad alimentaria
    "anexo-d",                 # vida útil / conservación
    "anexo-b",                 # mermas aceptables
    "cap2-faltas",             # clasificación de faltas
    "cap5-kpis",               # KPIs
]

PREAMBLE = r"""
\usepackage{{fancyhdr}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot[L]{{\small {code}}}
\fancyfoot[C]{{\small \thepage}}
\fancyfoot[R]{{\small {name}}}
\renewcommand{{\headrulewidth}}{{0pt}}
\renewcommand{{\footrulewidth}}{{0.4pt}}
\fancypagestyle{{plain}}{{%
  \fancyhf{{}}
  \fancyfoot[L]{{\small {code}}}
  \fancyfoot[C]{{\small \thepage}}
  \fancyfoot[R]{{\small {name}}}
  \renewcommand{{\headrulewidth}}{{0pt}}
  \renewcommand{{\footrulewidth}}{{0.4pt}}
}}
\usepackage{{enumitem}}
\setlist{{nosep, topsep=2pt, partopsep=0pt, itemsep=1pt}}
\usepackage{{titlesec}}
\titlespacing*{{\section}}{{0pt}}{{2.2ex plus 1ex minus .2ex}}{{1ex}}
\titlespacing*{{\subsection}}{{0pt}}{{1.6ex plus .8ex}}{{.6ex}}
"""


def preprocess(md: str, brand: dict) -> str:
    md = re.sub(r"\{\{\s*brand\.name\s*\}\}", brand["name"], md)
    md = re.sub(r"\{\{\s*brand\.short\s*\}\}", brand["short"], md)
    md = re.sub(r"\{\{\s*brand\.code\s*\}\}", brand["code"], md)

    kept = []
    for ln in md.split("\n"):
        if ".md-button" in ln:            # botones de descarga (sin sentido en papel)
            continue
        if ln.lstrip().startswith("[⬇"):
            continue
        if re.match(r"^---\s*$", ln):      # separadores temáticos: ruido en PDF
            continue
        kept.append(ln)
    md = "\n".join(kept)

    md = md.replace("☐", "[ ]")            # casilla -> imprimible con Latin Modern
    md = md.replace("│", "|")              # conector del organigrama (U+2502 no está en la fuente)
    md = re.sub(r"_{2,}", lambda _m: r"`\rule{2.5cm}{0.4pt}`{=latex}", md)  # campos en blanco
    return md


def assemble(files: list[str], brand: dict, title: str) -> str:
    meta = (
        "---\n"
        f'title: "{title}"\n'
        f'subtitle: "{brand["name"]}"\n'
        'date: "Versión 1.0"\n'
        "lang: es\n"
        "---\n\n"
    )
    parts = [preprocess((DOCS / f"{f}.md").read_text(encoding="utf-8"), brand)
             for f in files]
    return meta + "\n\n".join(parts) + "\n"


def run_pandoc(md: str, brand: dict, out_pdf: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        md_path = Path(tmp) / "doc.md"
        pre_path = Path(tmp) / "preamble.tex"
        md_path.write_text(md, encoding="utf-8")
        pre_path.write_text(PREAMBLE.format(code=brand["code"], name=brand["name"]), encoding="utf-8")
        subprocess.run(
            [
                "pandoc", str(md_path), "-o", str(out_pdf),
                "--pdf-engine=xelatex",
                "--toc", "--toc-depth=2",
                f"--include-in-header={pre_path}",
                "-V", "documentclass=article",
                "-V", "geometry:margin=2.3cm",
                "-V", "fontsize=11pt",
                "-V", "colorlinks=true", "-V", "linkcolor=black", "-V", "toccolor=black",
            ],
            check=True,
        )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    brands = sorted((p.stem, yaml.safe_load(p.read_text(encoding="utf-8")))
                    for p in BRANDS_DIR.glob("*.yml"))
    for bid, brand in brands:
        print(f"\n=== {brand['name']} ({bid}) ===")
        run_pandoc(assemble(FULL, brand, "Manual de Operación"),
                   brand, OUT / f"manual-completo-{bid}.pdf")
        print(f"  pdf/manual-completo-{bid}.pdf")
        run_pandoc(assemble(QUICK, brand, "Referencia Rápida de Operación"),
                   brand, OUT / f"referencia-rapida-{bid}.pdf")
        print(f"  pdf/referencia-rapida-{bid}.pdf")


if __name__ == "__main__":
    main()
