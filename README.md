# Manual de Operación

Sitio web del Manual de Operación, construido con [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).
Una sola fuente de contenido genera un sitio por marca (Brown, Aluxe, …).

## Estructura

| Ruta | Qué es |
| ----- | ----- |
| `docs/` | Contenido del manual (una página por sección). **Fuente editable.** |
| `brands/*.yml` | Configuración por marca (nombre, nombre corto, código de documento, colores de acento). |
| `params.yml` | Parámetros operativos de referencia (p. ej. calibración de espresso). **Fuente única** que consumen el sitio y los PDF. |
| `main.py` | Módulo de macros: inyecta la marca y los parámetros en las páginas (`{{ brand.name }}`, `{{ espresso.dosis.rango }}`, etc.). |
| `mkdocs.yml` | Configuración del sitio (tema, navegación, plugins). |
| `scripts/gen_brand_css.py` | Genera `docs/stylesheets/brand.css` con los colores de la marca activa (no se versiona). |
| `scripts/build_formatos_pdf.py` | Genera los formatos imprimibles en PDF (`docs/descargas/`). |
| `scripts/build_all.py` | Construye un sitio por marca en `site/<marca>/` + portada. |
| `scripts/build_manual_pdf.py` | Orquesta los PDF imprimibles del manual en `pdf/` (requiere pandoc + lualatex). |
| `latex/` | Diseño de los PDF: `preamble.tex` (tipografía, encabezados, cajas), `cover.tex` (portada) y `filters/manual.lua` (adapta los componentes web a imprenta). |
| `scripts/split_manual.py` | Migración única del `.md` original a `docs/` (registro histórico). |
| `archive/` | Artefactos de la migración inicial (el `.md` original y scripts de arreglo puntuales). Solo referencia histórica. |

## Desarrollo local

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt

python scripts/gen_brand_css.py        # genera docs/stylesheets/brand.css (no se versiona)
python scripts/build_formatos_pdf.py   # genera los PDF (necesarios para --strict)
mkdocs serve                            # vista previa en http://127.0.0.1:8000
```

> `brand.css` está en `.gitignore`; sin este primer paso el sitio se sirve sin los colores de marca.

Por defecto se usa la marca `brown`. Para previsualizar otra:

```bash
BRAND=aluxe python scripts/build_formatos_pdf.py
BRAND=aluxe SITE_NAME="Manual de Operación — Aluxe" mkdocs serve
```

## Construir todos los sitios

```bash
python scripts/build_all.py   # -> site/index.html + site/<marca>/
```

> Cada marca sobrescribe en el sitio `docs/stylesheets/brand.css` y `docs/descargas/*.pdf`. Ambos están en `.gitignore`, así que al terminar el árbol de trabajo queda con los archivos de la última marca construida (irrelevante para el sitio publicado, útil de saber al previsualizar con `mkdocs serve`).

## PDFs imprimibles del manual

Requiere `pandoc` y `lualatex` (TeX Live) instalados.

```bash
python scripts/build_manual_pdf.py   # -> pdf/manual-completo-<marca>.pdf y pdf/referencia-rapida-<marca>.pdf
```

- **Manual completo:** todo el manual con portada, índice y pie de "documento controlado". Para el fólder oficial y el acuse.
- **Referencia rápida:** solo lo operativo (parámetros de café, seguridad, emergencias, vida útil, mermas, faltas, KPIs). Para tener en barra.

Cómo funciona (y por qué regenerar es trivial cuando el manual cambia):

- La **estructura se deriva del `nav` de `mkdocs.yml`**: cada grupo del menú es un capítulo del PDF y cada página una sección. Páginas nuevas o reordenamientos aparecen solos en el PDF completo; solo la lista `QUICK` (qué merece estar en barra) es curada a mano en `scripts/build_manual_pdf.py`.
- Las macros `{{ brand.* }}` / `{{ espresso.* }}` se resuelven desde `brands/` y `params.yml`; una macro desconocida detiene la construcción.
- Los componentes web (admonitions, spec tiles, KPIs, chips, timeline) se convierten a equivalentes de imprenta en `latex/filters/manual.lua`, trabajando sobre el AST de pandoc. El diseño (portada, colores de marca, cajas de aviso, encabezados) vive en `latex/`.
- Los builds son **reproducibles byte a byte**: la fecha se fija al último commit que tocó las fuentes (`SOURCE_DATE_EPOCH`) y se usa lualatex (xelatex aleatoriza los tags de subsetting de fuentes). Mismo commit → PDFs idénticos.
- La versión del documento vive en `params.yml` (`manual.version`); súbela al liberar una revisión formal.

## Agregar una marca

1. Crea `brands/<marca>.yml` con `name`, `short` y `code`.
2. Vuelve a construir (`scripts/build_all.py`). Se genera automáticamente.

## Publicar (GitHub Pages)

El deploy es automático vía GitHub Actions (`.github/workflows/deploy.yml`) en cada push a `main`.

**Requisito único (una sola vez):** en GitHub → *Settings → Pages → Source* = **GitHub Actions**.

URLs resultantes:

- Portada: `https://skalas.github.io/manual-operaciones-cafe/`
- Brown: `https://skalas.github.io/manual-operaciones-cafe/brown/`
- Aluxe: `https://skalas.github.io/manual-operaciones-cafe/aluxe/`
