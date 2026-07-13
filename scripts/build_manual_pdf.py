"""Genera los PDF imprimibles del manual (pandoc + XeLaTeX), por marca.

Salida (local, no se publica en el sitio):
    pdf/manual-completo-<marca>.pdf
    pdf/referencia-rapida-<marca>.pdf

Diseño del pipeline (reproducible: docs/ es la única fuente):
  * La estructura del manual completo se deriva del `nav` de mkdocs.yml:
    cada grupo del menú es un capítulo del PDF y cada página una sección.
    Si el manual cambia (páginas nuevas, reordenamientos), el PDF lo sigue
    sin tocar este script.
  * Las macros {{ x.y }} se resuelven de forma genérica desde params.yml y
    brands/<marca>.yml; una macro desconocida detiene la construcción.
  * La adaptación web -> impreso vive en latex/filters/manual.lua (sobre el
    AST de pandoc) y el diseño en latex/preamble.tex y latex/cover.tex.
    Este script solo genera defs.tex (marca, colores, versión) y orquesta.
  * SOURCE_DATE_EPOCH se fija al último commit para builds deterministas.

Uso:  python scripts/build_manual_pdf.py
Requiere pandoc y xelatex en el PATH.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "pdf"
BRANDS_DIR = ROOT / "brands"
LATEX = ROOT / "latex"

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

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --- Estructura del manual: derivada del nav de mkdocs.yml -----------------

def nav_entries() -> list[tuple[str, list[tuple[str, str]] | str]]:
    """Devuelve el nav como [(etiqueta, 'archivo')] o [(etiqueta, [(etiqueta, archivo), …])]."""

    class MkDocsLoader(yaml.SafeLoader):
        """Ignora los tags específicos de MkDocs (!ENV, !!python/name:…)."""

    MkDocsLoader.add_multi_constructor("!", lambda loader, suffix, node: None)
    MkDocsLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/name:", lambda loader, suffix, node: None)

    cfg = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), MkDocsLoader)
    entries = []
    for item in cfg["nav"]:
        (label, value), = item.items()
        if isinstance(value, str):
            entries.append((label, value.removesuffix(".md")))
        else:
            pages = [(pl, pv.removesuffix(".md"))
                     for page in value for pl, pv in page.items()]
            entries.append((label, pages))
    return entries


# --- Preprocesamiento de cada página ----------------------------------------

MACRO_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")


def resolve_macros(md: str, ctx: dict, fname: str) -> str:
    """Sustituye {{ ruta.con.puntos }} desde ctx; falla si la macro no existe."""
    def sub(m: re.Match) -> str:
        cur = ctx
        for part in m.group(1).split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(f"Macro desconocida {{{{ {m.group(1)} }}}} en docs/{fname}.md")
            cur = cur[part]
        return str(cur)
    return MACRO_RE.sub(sub, md)


def strip_front_matter(md: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.DOTALL)


def strip_web_only_lines(md: str) -> str:
    """Quita lo que solo existe para la web y pandoc no debe ver.

    Enlaces de navegación de las tarjetas ("Entrar"/"Abrir"), el eyebrow del
    hero, los shortcodes de iconos y los attr-lists de clase ({ .lg }); los
    de anclaje ({ #id }) se conservan.
    """
    md = re.sub(r"^\s*\[:octicons-arrow[-\w]*:[^\]]*\]\([^)]*\)\s*$", "", md, flags=re.M)
    md = re.sub(r'^<p class="eyebrow">.*</p>$', "", md, flags=re.M)
    # El espacio que sigue al icono también se quita: dejarlo movería una
    # columna el contenido de los ítems de lista y sus párrafos de
    # continuación (indentados a 4 espacios) se volverían bloques de código.
    md = re.sub(r":(material|octicons|fontawesome)[-\w]*:\s?", "", md)
    md = re.sub(r"\{\s*\.[\w. -]+\}\s?", "", md)
    return md


def admonitions_to_divs(md: str) -> str:
    """Convierte `!!! tipo "Título"` (sintaxis de Material) a divs de pandoc.

    Pandoc no entiende `!!!`; con un fenced div (::: {.admonition .tipo}) el
    filtro Lua lo convierte en una caja tcolorbox conservando el contenido.
    """
    out: list[str] = []
    in_body = False
    for ln in md.split("\n"):
        m = re.match(r'^(?:!!!|\?\?\?\+?)\s+([\w-]+)(?:\s+"([^"]*)")?\s*$', ln)
        if m:
            if in_body:                 # admonition consecutivo: cerrar el anterior
                out += [":::", ""]
            kind, title = m.group(1), m.group(2)
            attrs = f".admonition .{kind}" + (f' title="{title}"' if title else "")
            out += [f"::: {{{attrs}}}", ""]
            in_body = True
            continue
        if in_body:
            if ln.strip() == "":
                out.append("")
                continue
            if ln.startswith("    "):
                out.append(ln[4:])
                continue
            out += [":::", ""]
            in_body = False
        out.append(ln)
    if in_body:
        out.append(":::")
    return "\n".join(out)


def shift_headings(md: str) -> str:
    """Baja todos los encabezados un nivel (# -> ##), sin tocar bloques de código."""
    out, in_fence = [], False
    for ln in md.split("\n"):
        if re.match(r"^(```|~~~)", ln):
            in_fence = not in_fence
        elif not in_fence and re.match(r"^#{1,5} ", ln):
            ln = "#" + ln
        out.append(ln)
    return "\n".join(out)


def drop_first_h1(md: str) -> str:
    return re.sub(r"^# .*\n", "", md, count=1, flags=re.M)


def page_body(fname: str, ctx: dict, *, shift: bool) -> str:
    md = (DOCS / f"{fname}.md").read_text(encoding="utf-8")
    md = strip_front_matter(md)
    md = resolve_macros(md, ctx, fname)
    md = strip_web_only_lines(md)
    md = admonitions_to_divs(md)
    if shift:
        md = shift_headings(md)
    return md


def assemble_full(ctx: dict) -> str:
    """Manual completo: grupos del nav como capítulos, páginas como secciones."""
    parts: list[str] = []
    for label, value in nav_entries():
        if isinstance(value, str):
            # Página suelta (Inicio, Introducción, Formatos): capítulo propio.
            parts.append(f"# {label}")
            parts.append(drop_first_h1(page_body(value, ctx, shift=False)))
        else:
            parts.append(f"# {label}")
            for _plabel, fname in value:
                parts.append(page_body(fname, ctx, shift=True))
    return "\n\n".join(parts) + "\n"


def assemble_quick(ctx: dict) -> str:
    """Referencia rápida: cada página seleccionada es un capítulo (su propio H1)."""
    return "\n\n".join(page_body(f, ctx, shift=False) for f in QUICK) + "\n"


# --- LaTeX: defs.tex generado + pandoc ---------------------------------------

def latex_escape(text: str) -> str:
    return re.sub(r"([&%$#_{}])", r"\\\1", text)


def defs_tex(brand: dict, title: str, version: str, doc_date: str) -> str:
    accent = brand["accent"].lstrip("#").upper()
    accent_light = brand["accent_light"].lstrip("#").upper()
    return (
        "% Generado por scripts/build_manual_pdf.py — no editar a mano.\n"
        "\\usepackage{xcolor}\n"
        f"\\definecolor{{BrandAccent}}{{HTML}}{{{accent}}}\n"
        f"\\definecolor{{BrandAccentLight}}{{HTML}}{{{accent_light}}}\n"
        f"\\newcommand{{\\BrandName}}{{{latex_escape(brand['name'])}}}\n"
        f"\\newcommand{{\\DocCode}}{{{latex_escape(brand['code'])}}}\n"
        f"\\newcommand{{\\DocTitle}}{{{latex_escape(title)}}}\n"
        f"\\newcommand{{\\DocVersion}}{{{latex_escape(version)}}}\n"
        f"\\newcommand{{\\DocDate}}{{{doc_date}}}\n"
    )


def last_source_commit() -> tuple[int, str]:
    """(epoch, fecha en español) del último commit que tocó las fuentes del manual.

    El epoch alimenta SOURCE_DATE_EPOCH (builds deterministas); la fecha usa
    la zona horaria del commit, no la de la máquina que construye.
    """
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct %cd", "--date=format-local:%d %m %Y", "--",
         "docs", "params.yml", "brands", "mkdocs.yml", "latex", "scripts"],
        cwd=ROOT, capture_output=True, text=True,
    )
    stamp = result.stdout.split()
    if len(stamp) != 4:                       # fuera de un repo git
        now = time.localtime()
        return int(time.time()), f"{now.tm_mday} de {MESES[now.tm_mon - 1]} de {now.tm_year}"
    epoch, day, month, year = stamp
    return int(epoch), f"{int(day)} de {MESES[int(month) - 1]} de {year}"


def run_pandoc(md: str, brand: dict, title: str, version: str,
               epoch: int, doc_date: str, out_pdf: Path, toc_depth: int = 2) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        md_path = Path(tmp) / "doc.md"
        defs_path = Path(tmp) / "defs.tex"
        md_path.write_text(md, encoding="utf-8")
        defs_path.write_text(defs_tex(brand, title, version, doc_date),
                             encoding="utf-8")
        subprocess.run(
            [
                "pandoc", str(md_path), "-o", str(out_pdf),
                # lualatex y no xelatex: con SOURCE_DATE_EPOCH produce PDFs
                # byte-idénticos entre corridas (xdvipdfmx aleatoriza los tags
                # de subsetting de fuentes y rompe la reproducibilidad).
                "--pdf-engine=lualatex",
                "--toc", f"--toc-depth={toc_depth}",
                f"--lua-filter={LATEX / 'filters' / 'manual.lua'}",
                f"--include-in-header={defs_path}",
                f"--include-in-header={LATEX / 'preamble.tex'}",
                f"--include-before-body={LATEX / 'cover.tex'}",
                "-V", "documentclass=scrreprt",
                "-V", "classoption=oneside",
                "-V", "classoption=openany",
                "-V", "fontsize=11pt",
                "-V", "geometry:margin=2.2cm",
                "-V", "lang=es",
                "-V", "colorlinks=true",
                "-V", "linkcolor=black", "-V", "urlcolor=BrandAccent",
                "-V", "toccolor=black",
                "-V", f"title-meta={title} — {brand['name']}",
            ],
            check=True,
            env={**os.environ, "SOURCE_DATE_EPOCH": str(epoch)},
        )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    params = load_yaml(ROOT / "params.yml")
    version = params["manual"]["version"]
    epoch, doc_date = last_source_commit()
    brands = sorted((p.stem, load_yaml(p)) for p in BRANDS_DIR.glob("*.yml"))
    for bid, brand in brands:
        ctx = {**params, "brand": brand}
        print(f"\n=== {brand['name']} ({bid}) ===")
        run_pandoc(assemble_full(ctx), brand, "Manual de Operación",
                   version, epoch, doc_date, OUT / f"manual-completo-{bid}.pdf")
        print(f"  pdf/manual-completo-{bid}.pdf")
        run_pandoc(assemble_quick(ctx), brand, "Referencia Rápida de Operación",
                   version, epoch, doc_date, OUT / f"referencia-rapida-{bid}.pdf",
                   toc_depth=1)
        print(f"  pdf/referencia-rapida-{bid}.pdf")


if __name__ == "__main__":
    main()
