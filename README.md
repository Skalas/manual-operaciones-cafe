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
| `scripts/build_manual_pdf.py` | Genera los PDF imprimibles del manual en `pdf/` (requiere pandoc + xelatex). |
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

Requiere `pandoc` y `xelatex` instalados.

```bash
python scripts/build_manual_pdf.py   # -> pdf/manual-completo-<marca>.pdf y pdf/referencia-rapida-<marca>.pdf
```

- **Manual completo:** todo el manual con portada, índice y pie de "documento controlado". Para el fólder oficial y el acuse.
- **Referencia rápida:** solo lo operativo (parámetros de café, seguridad, emergencias, vida útil, mermas, faltas, KPIs). Para tener en barra.
- El contenido a incluir en cada uno se define en las listas `FULL` y `QUICK` de `scripts/build_manual_pdf.py`.

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
