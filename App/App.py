# -*- coding: utf-8 -*-
"""
App - Checklist QA/QC de Planos (Ubicación y Localización)
Interfaz Streamlit para llenar el checklist y generar el Acta en PDF.
"""
import streamlit as st
from datetime import date
import tempfile, os

# from generar_acta import generar_pdf # This import is no longer needed after combining


# Content of generar_acta.py (previously in cell Zrl2sKpiKGSE)
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame,
    PageTemplate, BaseDocTemplate, NextPageTemplate
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ---------------------------------------------------------------------------
# 1. PALETA Y ESTILOS
# ---------------------------------------------------------------------------
ROJO = colors.HexColor("#C8102E")      # rojo institucional
NEGRO = colors.HexColor("#1A1A1A")
GRIS_CLARO = colors.HexColor("#F2F2F2")
GRIS_MEDIO = colors.HexColor("#CCCCCC")
BLANCO = colors.white

styles = getSampleStyleSheet()

estilo_titulo = ParagraphStyle(
    "TituloActa", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=15, textColor=NEGRO,
    alignment=TA_CENTER, spaceAfter=2,
)
estilo_subtitulo = ParagraphStyle(
    "Subtitulo", parent=styles["Normal"],
    fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#555555"),
    alignment=TA_CENTER, spaceAfter=0,
)    
estilo_seccion = ParagraphStyle(
    "Seccion", parent=styles["Normal"],
    fontName="Helvetica-Bold", fontSize=10, textColor=BLANCO,
)
estilo_celda = ParagraphStyle(
    "Celda", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5,
    textColor=NEGRO, leading=11,
)
estilo_celda_bold = ParagraphStyle(
    "CeldaBold", parent=estilo_celda, fontName="Helvetica-Bold",
)

# ---------------------------------------------------------------------------
# 3. CABECERA Y PIE DE PÁGINA (dibujados en el canvas)
# ---------------------------------------------------------------------------
def dibujar_cabecera_pie(canvas, doc, datos_proyecto_dict): # Added datos_proyecto_dict as an argument
    canvas.saveState()
    ancho, alto = letter

    # --- Placeholder de logo SENCICO ---
        # --- Logo SENCICO ---
    x_logo, y_logo, w_logo, h_logo = 1.8*cm, alto - 2.6*cm, 2.6*cm, 1.6*cm
    ruta_logo = os.path.join(os.path.dirname(__file__), "logo_sencico.png")
    print("Buscando logo en:", ruta_logo, "-> existe:", os.path.exists(ruta_logo))
    if os.path.exists(ruta_logo):
        img = ImageReader(ruta_logo)
        iw, ih = img.getSize()
        aspecto = iw / ih

        # Ajustar la imagen dentro del recuadro manteniendo su proporción
        if w_logo / h_logo > aspecto:
            h_dibujo = h_logo
            w_dibujo = h_logo * aspecto
        else:
            w_dibujo = w_logo
            h_dibujo = w_logo / aspecto

        x_centrado = x_logo + (w_logo - w_dibujo) / 2
        y_centrado = y_logo + (h_logo - h_dibujo) / 2

        canvas.drawImage(img, x_centrado, y_centrado, width=w_dibujo, height=h_dibujo,
                          preserveAspectRatio=True, mask='auto')
    else:
        # Si no encuentra el archivo, muestra el placeholder como respaldo
        canvas.setStrokeColor(GRIS_MEDIO)
        canvas.setLineWidth(0.8)
        canvas.rect(x_logo, y_logo, w_logo, h_logo)
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawCentredString(x_logo + w_logo/2, y_logo + h_logo/2 - 2, "LOGO SENCICO")

    # --- Título institucional ---
    canvas.setFont("Helvetica-Bold", 13)
    canvas.setFillColor(NEGRO)
    canvas.drawCentredString(ancho/2, alto - 1.6*cm,
                              "ACTA DE REVISIÓN DE PLANO")
    canvas.setFont("Helvetica", 9.5)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawCentredString(ancho/2, alto - 2.15*cm,
                              "Checklist QA/QC — Plano de Ubicación y Localización")

    # --- N° de acta (esquina superior derecha) ---
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(ROJO)
    canvas.drawRightString(ancho - 1.8*cm, alto - 1.6*cm,
                            datos_proyecto_dict["N° de Acta"]) # Used datos_proyecto_dict
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(NEGRO)
    canvas.drawRightString(ancho - 1.8*cm, alto - 1.95*cm,
                            datos_proyecto_dict["Fecha de revisión"]) # Used datos_proyecto_dict

    # --- Franja roja de acento ---
    canvas.setFillColor(ROJO)
    canvas.rect(1.8*cm, alto - 2.85*cm, ancho - 3.6*cm, 0.09*cm, stroke=0, fill=1)

    # --- Pie de página ---
    canvas.setStrokeColor(GRIS_MEDIO)
    canvas.setLineWidth(0.5)
    canvas.line(1.8*cm, 2.6*cm, ancho - 1.8*cm, 2.6*cm)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(NEGRO)
    canvas.drawString(1.8*cm, 2.2*cm, "Firma del revisor: ____________________________")
    canvas.drawString(1.8*cm, 1.75*cm, "N° de colegiatura: ____________________")

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawRightString(ancho - 1.8*cm, 2.2*cm,
                            "Producto acádemico - Topografía y Geodesia - Ciclo I - Lectura de Planos")
    canvas.drawRightString(ancho - 1.8*cm, 1.85*cm, f"Página {doc.page}")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# 4. CONSTRUCCIÓN DEL CONTENIDO (Platypus)
# ---------------------------------------------------------------------------
def construir_tabla_datos(datos):
    filas = [
        ["Proyecto:", datos["Proyecto"], "Propietario:", datos["Propietario"]],
        ["Dirección:", datos["Dirección"], "Distrito / Provincia:", datos["Distrito / Provincia"]],
        ["Revisor:", datos["Revisor"], "Fecha de revisión:", datos["Fecha de revisión"]],
    ]
    filas_par = [
        [Paragraph(c, estilo_celda_bold) if i % 2 == 0 else Paragraph(c, estilo_celda)
         for i, c in enumerate(fila)]
        for fila in filas
    ]
    tabla = Table(filas_par, colWidths=[2.6*cm, 6.3*cm, 3.6*cm, 5.5*cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("BOX", (0, 0), (-1, -1), 0.6, GRIS_MEDIO),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabla


def color_estado(estado):
    return {
        "Cumple": (NEGRO, BLANCO),
        "No cumple": (colors.HexColor("#7A0C1E"), colors.HexColor("#FBDDE1")),
        "N/A": (colors.HexColor("#777777"), GRIS_CLARO),
    }.get(estado, (NEGRO, BLANCO))


def construir_tabla_checklist(checklist):
    story = []
    contador_total = 0
    contador_cumple = 0

    for titulo_seccion, items in checklist:
        # Encabezado de sección (fila roja)
        header = Table(
            [[Paragraph(titulo_seccion, estilo_seccion)]],
            colWidths=[17*cm],
        )
        header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ROJO),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(header)

        filas = [[
            Paragraph("N°", estilo_celda_bold),
            Paragraph("Ítem", estilo_celda_bold),
            Paragraph("Estado", estilo_celda_bold),
            Paragraph("Observación", estilo_celda_bold),
        ]]
        estilo_filas = [
            ("BACKGROUND", (0, 0), (-1, 0), GRIS_MEDIO),
        ]

        for idx, (item, estado, obs) in enumerate(items, start=1):
            contador_total += 1
            if estado == "Cumple":
                contador_cumple += 1
            color_txt, color_fondo = color_estado(estado)
            estilo_estado = ParagraphStyle(
                f"estado_{titulo_seccion}_{idx}", parent=estilo_celda,
                textColor=color_txt, fontName="Helvetica-Bold",
            )
            filas.append([
                Paragraph(str(idx), estilo_celda),
                Paragraph(item, estilo_celda),
                Paragraph(estado, estilo_estado),
                Paragraph(obs if obs else "—", estilo_celda),
            ])
            fila_i = len(filas) - 1
            estilo_filas.append(("BACKGROUND", (0, fila_i), (-1, fila_i), color_fondo))
            if fila_i % 2 == 0:
                pass  # ya coloreado por estado; se deja limpio para no competir colores

        tabla = Table(filas, colWidths=[1*cm, 7.5*cm, 2.7*cm, 5.8*cm], repeatRows=1)
        estilo_filas += [
            ("GRID", (0, 0), (-1, -1), 0.4, GRIS_MEDIO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]
        tabla.setStyle(TableStyle(estilo_filas))
        story.append(tabla)
        story.append(Spacer(1, 10))

    return story, contador_total, contador_cumple


def construir_resumen(total, cumple):
    porcentaje = round((cumple / total) * 100) if total else 0
    if porcentaje == 100:
        estado_general, color_estado_gral = "APTO", colors.HexColor("#1B7A3D")
    elif porcentaje >= 70:
        estado_general, color_estado_gral = "APTO CON OBSERVACIONES", colors.HexColor("#B8860B")
    else:
        estado_general, color_estado_gral = "NO APTO", ROJO

    estilo_resumen_txt = ParagraphStyle(
        "ResumenTxt", parent=estilo_celda, fontSize=10, fontName="Helvetica-Bold",
    )
    estilo_resumen_estado = ParagraphStyle(
        "ResumenEstado", parent=estilo_celda, fontSize=12, fontName="Helvetica-Bold",
        textColor=color_estado_gral,
    )

    tabla = Table(
        [[
            Paragraph(f"Cumplimiento: {cumple}/{total} ítems conformes ({porcentaje}%)", estilo_resumen_txt),
            Paragraph(f"Estado general: {estado_general}", estilo_resumen_estado),
        ]],
        colWidths=[9.5*cm, 7.5*cm],
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F7F7")),
        ("BOX", (0, 0), (-1, -1), 1, NEGRO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return tabla


# ---------------------------------------------------------------------------
# 5. ENSAMBLAJE DEL DOCUMENTO
# ---------------------------------------------------------------------------
def generar_pdf(ruta_salida, datos_proyecto_in, checklist_in):
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=3.2*cm, bottomMargin=3.0*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
    )

    story = []
    story.append(construir_tabla_datos(datos_proyecto_in))
    story.append(Spacer(1, 14))

    tablas_checklist, total, cumple = construir_tabla_checklist(checklist_in)
    story.extend(tablas_checklist)

    story.append(Spacer(1, 6))
    story.append(construir_resumen(total, cumple))

    doc.build(story, onFirstPage=lambda canvas, doc: dibujar_cabecera_pie(canvas, doc, datos_proyecto_in),
            onLaterPages=lambda canvas, doc: dibujar_cabecera_pie(canvas, doc, datos_proyecto_in))



# ---------------------------------------------------------------------------
# Plantilla del checklist (solo estructura: secciones e ítems, sin estado)
# ---------------------------------------------------------------------------
PLANTILLA_CHECKLIST = [
    ("1. DATOS GENERALES / MEMBRETE", [
        "Título correcto del plano",
        "Nombre del proyecto",
        "Nombre del propietario/solicitante",
        "Dirección completa del predio",
        "Distrito, provincia, departamento",
        "Número de plano y código de lámina",
        "Escala gráfica y numérica",
        "Fecha de elaboración",
        "Firma y sello del profesional responsable",
    ]),
    ("2. PLANO DE UBICACIÓN", [
        "Norte magnético/geográfico",
        "Nomenclatura de calles colindantes",
        "Identificación de manzana y lote",
        "Lotes vecinos identificados",
        "Cuadro de linderos y medidas perimétricas",
        "Ángulos internos del polígono",
        "Área total y perímetro",
        "Coordenadas UTM de vértices",
        "Zonificación / uso de suelo",
    ]),
    ("3. PLANO DE LOCALIZACIÓN", [
        "Referencia a hitos conocidos",
        "Ubicación dentro de la trama urbana",
        "Escala reducida diferenciada",
        "Vías principales de acceso rotuladas",
    ]),
    ("4. SIMBOLOGÍA", [
        "Leyenda/simbología utilizada",
        "Escala gráfica (barra)",
        "Achurado del polígono del terreno",
    ]),
    ("5. REGISTRAL / CATASTRAL", [
        "Partida registral (SUNARP)",
        "Código catastral municipal",
        "Certificado de parámetros (CPU)",
    ]),
]

ESTADOS = ["Cumple", "No cumple", "N/A"]

st.set_page_config(page_title="Checklist QA/QC - Planos", page_icon="📐", layout="wide")

st.title("📐 Checklist QA/QC — Plano de Ubicación y Localización")
st.caption("Revisión guiada de planos, con generación automática de Acta en PDF")

# ---------------------------------------------------------------------------
# 1. Datos del proyecto
# ---------------------------------------------------------------------------
st.header("1. Datos del proyecto")
col1, col2 = st.columns(2)
with col1:
    proyecto = st.text_input("Proyecto")
    direccion = st.text_input("Dirección")
    revisor = st.text_input("Revisor")
    n_acta = st.text_input("N° de Acta", value="ACTA-2026-001")
with col2:
    propietario = st.text_input("Propietario")
    distrito_provincia = st.text_input("Distrito / Provincia")
    fecha_revision = st.date_input("Fecha de revisión", value=date.today())

st.divider()

# ---------------------------------------------------------------------------
# 2. Checklist interactivo
# ---------------------------------------------------------------------------
st.header("2. Checklist")

respuestas = []  # (titulo_seccion, [(item, estado, observacion), ...])

for titulo_seccion, items in PLANTILLA_CHECKLIST:
    st.subheader(titulo_seccion)
    items_respondidos = []
    for item in items:
        c1, c2, c3 = st.columns([3, 1.3, 3])
        with c1:
            st.markdown(f"**{item}**")
        with c2:
            estado = st.radio(
                "Estado", ESTADOS, key=f"{titulo_seccion}_{item}_estado",
                horizontal=False, label_visibility="collapsed",
            )
        with c3:
            obs = ""
            if estado == "No cumple":
                obs = st.text_input(
                    "Observación", key=f"{titulo_seccion}_{item}_obs",
                    label_visibility="collapsed",
                    placeholder="Describe la observación...",
                )
        items_respondidos.append((item, estado, obs))
    respuestas.append((titulo_seccion, items_respondidos))
    st.markdown("---")

# ---------------------------------------------------------------------------
# 3. Resumen en pantalla
# ---------------------------------------------------------------------------
total_items = sum(len(items) for _, items in respuestas)
cumple_items = sum(
    1 for _, items in respuestas for (_, estado, _) in items if estado == "Cumple"
)
porcentaje = round((cumple_items / total_items) * 100) if total_items else 0

st.header("3. Resumen")
m1, m2, m3 = st.columns(3)
m1.metric("Ítems conformes", f"{cumple_items} / {total_items}")
m2.metric("Cumplimiento", f"{porcentaje}%")
if porcentaje == 100:
    m3.success("Estado: APTO")
elif porcentaje >= 70:
    m3.warning("Estado: APTO CON OBSERVACIONES")
else:
    m3.error("Estado: NO APTO")

st.divider()

# ---------------------------------------------------------------------------
# 4. Generar PDF
# ---------------------------------------------------------------------------
st.header("4. Generar Acta")

campos_completos = all([proyecto, propietario, direccion, distrito_provincia, revisor])
if not campos_completos:
    st.info("Completa los datos del proyecto (sección 1) para habilitar la generación del acta.")

if st.button("📄 Generar Acta en PDF", type="primary", disabled=not campos_completos):
    datos_proyecto = {
        "Proyecto": proyecto,
        "Propietario": propietario,
        "Dirección": direccion,
        "Distrito / Provincia": distrito_provincia,
        "Revisor": revisor,
        "Fecha de revisión": fecha_revision.strftime("%d/%m/%Y"),
        "N° de Acta": n_acta,
    }

    with tempfile.TemporaryDirectory() as tmp:
        ruta_pdf = os.path.join(tmp, f"{n_acta}.pdf")
        generar_pdf(ruta_pdf, datos_proyecto_in=datos_proyecto, checklist_in=respuestas)

        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()

    st.success("Acta generada correctamente.")
    st.download_button(
        "⬇️ Descargar Acta PDF",
        data=pdf_bytes,
        file_name=f"{n_acta}.pdf",
        mime="application/pdf",
    )
