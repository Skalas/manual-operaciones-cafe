"""Genera los formatos imprimibles del manual en PDF (para imprimir y firmar).

Salida: docs/descargas/<formato>.pdf (uno por formato) y
docs/descargas/formatos-todos.pdf (paquete con todos).

Los PDFs se sirven como archivos estáticos del sitio MkDocs y se enlazan desde
docs/formatos.md. Fuente única de la definición de campos: este script.

Requiere fpdf2 (ver requirements.txt). Ejecutar dentro del venv del proyecto:
    python scripts/build_formatos_pdf.py
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "descargas"

_brand_id = os.environ.get("BRAND", "brown")
_brand = yaml.safe_load((ROOT / "brands" / f"{_brand_id}.yml").read_text(encoding="utf-8"))
BRAND = _brand["name"]

# Parámetros operativos: fuente única compartida con el sitio (ver params.yml).
_params = yaml.safe_load((ROOT / "params.yml").read_text(encoding="utf-8"))
_esp = _params["espresso"]


def _esp_line(key: str) -> str:
    p = _esp[key]
    # fpdf2 con fuentes core usa latin-1: el guion largo (–) no es representable.
    return f"{p['rango'].replace('–', '-')} {p['unidad']}"


ESPRESSO_NOTE = (
    f"Parámetros de referencia: dosis {_esp_line('dosis')}, "
    f"rendimiento {_esp_line('rendimiento')}, tiempo {_esp_line('tiempo')}, "
    f"temperatura {_esp_line('temperatura')}."
)

# --- Definición de formatos (misma estructura que docs/formatos.md) ---
# Cada bloque: ("fields", [labels]) | ("check", [items]) | ("table", (headers, n_rows))
#              | ("text", "parrafo") | ("note", "linea gris")

FORMATOS: list[dict] = [
    {
        "file": "acuse-recibido",
        "title": "Acuse de Recibido del Manual",
        "ref": "Referencia: apartado 2.1, art. 22.",
        "blocks": [
            ("text", "Declaro que recibí, leí y comprendí el Manual de Operación de "
                     f"{BRAND}, y me comprometo a cumplir las disposiciones "
                     "contenidas en él."),
            ("fields", ["Nombre del colaborador", "Puesto", "Fecha",
                        "Versión del manual recibida", "Firma"]),
        ],
    },
    {
        "file": "reporte-incidencia",
        "title": "Reporte de Incidencia Interna",
        "ref": "Referencia: apartados 1.3, 2.3 y 2.4.",
        "blocks": [
            ("fields", ["Folio", "Fecha del reporte", "Hora", "Lugar",
                        "Reporta (nombre / puesto)", "Personas involucradas",
                        "Tipo (operación / seguridad / RH / administración / ética)",
                        "Descripción de los hechos", "Evidencias disponibles",
                        "Posibles testigos", "Recibió (nombre / puesto)",
                        "Responsable de seguimiento"]),
            ("check", ["Leve", "Grave", "Muy grave", "Requiere investigación"]),
        ],
    },
    {
        "file": "checklist-turno",
        "title": "Checklist de Apertura y Cierre de Turno",
        "ref": "Referencia: apartados 4.1 y 4.4.",
        "blocks": [
            ("fields", ["Fecha", "Turno (apertura / cierre)", "Responsable"]),
            ("subtitle", "Apertura"),
            ("check", ["Máquina estabilizada", "Presión correcta", "Temperatura correcta",
                       "Molino limpio y calibrado", "Tolva limpia", "Café fresco disponible",
                       "Agua disponible", "Filtros limpios", "Vaporizadores purgados",
                       "Fondo de caja verificado", "Áreas y estaciones limpias"]),
            ("subtitle", "Cierre"),
            ("check", ["Molino cepillado y purgado", "Superficies y barra limpias",
                       "Loza lavada", "Equipo apagado / en modo seguro",
                       "Producto etiquetado y rotado (PEPS)", "Corte de caja realizado",
                       "Incidencias registradas"]),
        ],
    },
    {
        "file": "bitacora-calibracion",
        "title": "Bitácora de Calibración de Espresso",
        "ref": "Referencia: apartado 4.1, art. 6.",
        "blocks": [
            ("table", (["Fecha", "Hora", "Café / lote", "Dosis (g)", "Rend. (g)",
                        "Tiempo (s)", "Temp. (C)", "Responsable"], 12)),
            ("note", ESPRESSO_NOTE),
        ],
    },
    {
        "file": "registro-mermas",
        "title": "Registro de Mermas",
        "ref": "Referencia: apartado 4.2, art. 8.",
        "blocks": [
            ("table", (["Fecha", "Producto", "Cantidad",
                        "Motivo (operativa/producción/caducidad/daño/extraord.)",
                        "Responsable"], 14)),
            ("note", "Parámetros aceptables: Anexo B (Mermas Operativas Aceptables por Categoría)."),
        ],
    },
    {
        "file": "registro-consumo",
        "title": "Registro de Consumo Interno",
        "ref": "Referencia: apartado 4.4, art. 10.",
        "blocks": [
            ("table", (["Fecha", "Producto", "Cantidad", "Motivo",
                        "Autorizó (nombre / puesto)"], 14)),
            ("note", "Bebida de cortesía del personal: una (1) por turno, cualquier bebida del menú (4.4)."),
        ],
    },
    {
        "file": "arqueo-caja",
        "title": "Arqueo / Corte de Caja",
        "ref": "Referencia: apartado 4.3, arts. 9-11 y 18.",
        "blocks": [
            ("fields", ["Fecha", "Turno / responsable", "Fondo inicial",
                        "Ventas en efectivo (sistema)", "Ventas con terminal (sistema)",
                        "Efectivo contado", "Diferencia (faltante / sobrante)",
                        "Propinas", "Observaciones", "Entregó (firma)", "Recibió (firma)"]),
        ],
    },
    {
        "file": "reporte-incidente",
        "title": "Reporte de Incidente / Emergencia",
        "ref": "Referencia: apartados 3.1, 3.2 (art. 17) y 3.3.",
        "blocks": [
            ("fields", ["Folio", "Fecha y hora", "Tipo de incidente",
                        "Personas involucradas", "Descripción de los hechos",
                        "Acciones realizadas", "Daños materiales o personales",
                        "¿Se usó grabación de CCTV? (ver 3.3)", "Causa raíz (si se determina)",
                        "Acciones correctivas y preventivas", "Responsable del seguimiento",
                        "Fecha de cierre"]),
        ],
    },
]

# Caracteres fuera de latin-1 que las fuentes core no soportan.
SANITIZE = {
    "–": "-", "—": "-", "☐": "[  ]", "“": '"', "”": '"', "‘": "'", "’": "'",
}


def s(text: str) -> str:
    for a, b in SANITIZE.items():
        text = text.replace(a, b)
    return text


class PDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120)
        self.cell(0, 6, s(BRAND), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0)


def render_format(pdf: PDF, fmt: dict) -> None:
    pdf.add_page()
    epw = pdf.epw  # ancho útil

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, s(fmt["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120)
    pdf.multi_cell(0, 5, s(fmt["ref"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(3)

    for kind, payload in fmt["blocks"]:
        if kind == "text":
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5.5, s(payload), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        elif kind == "subtitle":
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, s(payload), new_x="LMARGIN", new_y="NEXT")
        elif kind == "note":
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(120)
            pdf.multi_cell(0, 4.5, s(payload), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0)
        elif kind == "fields":
            pdf.set_font("Helvetica", "", 10)
            for label in payload:
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 7, s(label) + ":", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(180)
                y = pdf.get_y() + 4
                pdf.line(pdf.l_margin, y, pdf.l_margin + epw, y)
                pdf.ln(7)
        elif kind == "check":
            pdf.set_font("Helvetica", "", 10)
            for item in payload:
                pdf.cell(0, 6.5, s("[  ]  " + item), new_x="LMARGIN", new_y="NEXT")
        elif kind == "table":
            headers, n_rows = payload
            pdf.set_font("Helvetica", "", 8)
            with pdf.table(text_align="LEFT", line_height=7, first_row_as_headings=True) as table:
                head = table.row()
                for h in headers:
                    head.cell(s(h))
                for _ in range(n_rows):
                    row = table.row()
                    for _ in headers:
                        row.cell("")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # PDFs individuales
    for fmt in FORMATOS:
        pdf = PDF(format="Letter")
        pdf.set_auto_page_break(True, margin=15)
        pdf.set_title(f"{fmt['title']} - {BRAND}")
        render_format(pdf, fmt)
        pdf.output(str(OUT / f"{fmt['file']}.pdf"))
        print(f"  docs/descargas/{fmt['file']}.pdf")

    # Paquete con todos
    pack = PDF(format="Letter")
    pack.set_auto_page_break(True, margin=15)
    pack.set_title(f"Formatos y Plantillas - {BRAND}")
    for fmt in FORMATOS:
        render_format(pack, fmt)
    pack.output(str(OUT / "formatos-todos.pdf"))
    print("  docs/descargas/formatos-todos.pdf")

    print(f"\nTotal: {len(FORMATOS)} formatos + 1 paquete.")


if __name__ == "__main__":
    main()
