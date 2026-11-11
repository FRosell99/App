# -*- coding: utf-8 -*-
"""
Gráfico del polígono (matplotlib) y reporte PDF (reportlab).
"""
from __future__ import annotations

import io
import math
import os
from datetime import date
from decimal import Decimal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from poligono_calculos import Resultado, grados_a_gms  # noqa: E402

# ---------------------------------------------------------------------------
# Paleta (misma línea gráfica que el Acta QA/QC)
# ---------------------------------------------------------------------------
ROJO = colors.HexColor("#C8102E")
NEGRO = colors.HexColor("#1A1A1A")
GRIS_CLARO = colors.HexColor("#F2F2F2")
GRIS_MEDIO = colors.HexColor("#CCCCCC")
GRIS_TEXTO = colors.HexColor("#555555")
BLANCO = colors.white

ROJO_HEX = "#C8102E"
AZUL_HEX = "#1F4E79"

RUTA_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_sencico.png")

NOMBRE_METODO = {
    "coordenadas": "Coordenadas UTM / locales — Fórmula de Gauss (determinantes)",
    "triangulacion": "Lados y diagonales — Triangulación y fórmula de Herón",
    "angulos": "Lados y ángulos internos — Poligonal cerrada + fórmula de Gauss",
}


# ---------------------------------------------------------------------------
# Formato numérico
# ---------------------------------------------------------------------------
def fmt(x: float, dec: int = 3) -> str:
    txt = f"{x:,.{dec}f}"
    # Evita mostrar "-0.000" cuando el valor redondeado es cero
    return txt.lstrip("-") if txt.strip("-0.,") == "" else txt


# ---------------------------------------------------------------------------
# Gráfico
# ---------------------------------------------------------------------------
def generar_grafico(res: Resultado, ancho_pulg: float = 7.0, alto_pulg: float = 5.4,
                    dpi: int = 200) -> bytes:
    """Devuelve una imagen PNG con el polígono dibujado."""
    coords = res.coords
    n = len(coords)
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    cx, cy = sum(xs) / n, sum(ys) / n
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0

    fig, ax = plt.subplots(figsize=(ancho_pulg, alto_pulg), dpi=dpi)
    ax.add_patch(MplPolygon(coords, closed=True, facecolor="#C8102E22",
                            edgecolor=ROJO_HEX, linewidth=1.8, zorder=2))

    # Diagonales de la triangulación
    if res.metodo == "triangulacion" and n > 3:
        for k in range(2, n - 1):
            ax.plot([coords[0][0], coords[k][0]], [coords[0][1], coords[k][1]],
                    linestyle="--", color="#888888", linewidth=0.9, zorder=1)
            mx = coords[0][0] + 0.7 * (coords[k][0] - coords[0][0])
            my = coords[0][1] + 0.7 * (coords[k][1] - coords[0][1])
            ax.text(mx, my, f"{res.diagonales[k - 2][1]:.2f}", fontsize=7, color="#666666",
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))

    # Distancias en el punto medio de cada lado, desplazadas hacia afuera
    signo_orient = 1 if _area_signo(coords) > 0 else -1
    off = span * 0.035
    for i in range(n):
        p, q = coords[i], coords[(i + 1) % n]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1.0
        # normal exterior: a la derecha para antihorario, izquierda para horario
        nx, ny = dy / L * signo_orient, -dx / L * signo_orient
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90:
            ang -= 180
        elif ang < -90:
            ang += 180
        ax.text(mx + nx * off, my + ny * off, f"{res.distancias[i]:.2f} m", fontsize=7.5,
                color=AZUL_HEX, ha="center", va="center", rotation=ang,
                rotation_mode="anchor", zorder=4)

    # Vértices
    ax.scatter(xs, ys, s=22, color=NEGRO_HEX, zorder=5)
    for i, (x, y) in enumerate(coords):
        vx, vy = x - cx, y - cy
        d = math.hypot(vx, vy) or 1.0
        ax.text(x + vx / d * off * 1.3, y + vy / d * off * 1.3, res.nombres[i],
                fontsize=10, fontweight="bold", ha="center", va="center", zorder=6)

    # Área al centro
    ax.text(cx, cy, f"A = {res.area:,.2f} m²\n({res.area_ha:,.4f} ha)", fontsize=9,
            ha="center", va="center", color="#7A0C1E", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=ROJO_HEX, alpha=0.9), zorder=7)

    margen = span * 0.12
    x0 = (min(xs) + max(xs)) / 2 - span / 2 - margen
    y0 = (min(ys) + max(ys)) / 2 - span / 2 - margen
    ax.set_xlim(x0, x0 + span + 2 * margen)
    ax.set_ylim(y0, y0 + span + 2 * margen)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":", linewidth=0.5, color="#BBBBBB")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.tick_params(labelsize=7)
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(30)
    if res.coords_dadas:
        ax.set_xlabel("Este (m)", fontsize=8)
        ax.set_ylabel("Norte (m)", fontsize=8)
    else:
        ax.set_xlabel("X local (m)", fontsize=8)
        ax.set_ylabel("Y local (m)", fontsize=8)

    # Flecha del Norte
    ax.annotate("N", xy=(0.95, 0.95), xytext=(0.95, 0.82), xycoords="axes fraction",
                ha="center", va="center", fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4))

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    return buf.getvalue()


NEGRO_HEX = "#1A1A1A"


def _area_signo(coords):
    s = 0.0
    for i in range(len(coords)):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % len(coords)]
        s += x1 * y2 - x2 * y1
    return s / 2


# ---------------------------------------------------------------------------
# Estilos PDF
# ---------------------------------------------------------------------------
_styles = getSampleStyleSheet()
st_seccion = ParagraphStyle("Seccion", parent=_styles["Normal"], fontName="Helvetica-Bold",
                            fontSize=10, textColor=BLANCO)
st_celda = ParagraphStyle("Celda", parent=_styles["Normal"], fontName="Helvetica",
                          fontSize=8.5, leading=11, textColor=NEGRO)
st_celda_b = ParagraphStyle("CeldaB", parent=st_celda, fontName="Helvetica-Bold")
st_nota = ParagraphStyle("Nota", parent=st_celda, fontSize=7.5, leading=10, textColor=GRIS_TEXTO)
st_formula = ParagraphStyle("Formula", parent=st_celda, fontSize=9, leading=13,
                            alignment=TA_CENTER)
st_area = ParagraphStyle("Area", parent=st_celda, fontName="Helvetica-Bold", fontSize=13,
                         leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#7A0C1E"))

ANCHO_UTIL = A4[0] - 3.6 * cm


def _encabezado_seccion(texto):
    t = Table([[Paragraph(texto, st_seccion)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ROJO),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _bloque(titulo, tabla):
    """Título de sección + tabla; se mantienen juntos si la tabla es corta."""
    contenido = [_encabezado_seccion(titulo), Spacer(1, 4), tabla]
    return [KeepTogether(contenido)] if len(tabla._cellvalues) <= 30 else contenido


def _tabla(filas, anchos, alinear_derecha_desde=1, fila_total=False):
    t = Table(filas, colWidths=anchos, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), NEGRO),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (alinear_derecha_desde - 1, -1), "CENTER"),
        ("ALIGN", (alinear_derecha_desde, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS_MEDIO),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(filas)):
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), GRIS_CLARO))
    if fila_total:
        estilo += [
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FBDDE1")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(estilo))
    return t


# ---------------------------------------------------------------------------
# Tablas de contenido
# ---------------------------------------------------------------------------
def tabla_datos_proyecto(datos: dict):
    claves = list(datos.items())
    filas = []
    for i in range(0, len(claves), 2):
        fila = []
        for k, v in claves[i:i + 2]:
            fila += [Paragraph(f"{k}:", st_celda_b), Paragraph(str(v) or "—", st_celda)]
        while len(fila) < 4:
            fila += ["", ""]
        filas.append(fila)
    t = Table(filas, colWidths=[2.9 * cm, 5.6 * cm, 2.9 * cm, ANCHO_UTIL - 11.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("BOX", (0, 0), (-1, -1), 0.6, GRIS_MEDIO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def tabla_coordenadas(res: Resultado, titulo_x="ESTE (m)", titulo_y="NORTE (m)"):
    n = res.n
    filas = [["VÉRTICE", "LADO", "DISTANCIA (m)", "ÁNG. INTERNO", "AZIMUT", titulo_x, titulo_y]]
    for i in range(n):
        ang = grados_a_gms(res.angulos[i]) if res.angulos else "—"
        filas.append([
            res.nombres[i], res.lados[i], fmt(res.distancias[i]), ang,
            grados_a_gms(res.azimuts[i]) if res.azimuts else "—",
            fmt(res.coords[i][0]), fmt(res.coords[i][1]),
        ])
    filas.append(["", "PERÍMETRO", fmt(res.perimetro), "", "", "", ""])
    anchos = [1.6 * cm, 1.9 * cm, 2.5 * cm, 2.4 * cm, 2.4 * cm, 3.2 * cm]
    anchos.append(ANCHO_UTIL - sum(anchos))
    return _tabla(filas, anchos, alinear_derecha_desde=2, fila_total=True)


def tabla_lados(res: Resultado):
    filas = [["N°", "LADO", "DISTANCIA (m)", "ÁNGULO INTERNO"]]
    for i in range(res.n):
        ang = grados_a_gms(res.angulos[i]) if res.angulos else "—"
        filas.append([str(i + 1), res.lados[i], fmt(res.distancias[i]),
                      f"{res.nombres[i]}: {ang}"])
    filas.append(["", "PERÍMETRO", fmt(res.perimetro), ""])
    if res.diagonales:
        filas.append(["", "DIAGONALES", "", ""])
        for nom, d in res.diagonales:
            filas.append(["", nom, fmt(d), ""])
    anchos = [1.2 * cm, 3.5 * cm, 3.5 * cm, ANCHO_UTIL - 8.2 * cm]
    t = _tabla(filas, anchos, alinear_derecha_desde=2)
    idx_per = res.n + 1
    extra = [
        ("BACKGROUND", (0, idx_per), (-1, idx_per), colors.HexColor("#FBDDE1")),
        ("FONTNAME", (0, idx_per), (-1, idx_per), "Helvetica-Bold"),
    ]
    if res.diagonales:
        extra += [
            ("BACKGROUND", (0, idx_per + 1), (-1, idx_per + 1), GRIS_MEDIO),
            ("FONTNAME", (0, idx_per + 1), (-1, idx_per + 1), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(extra))
    return t


def tabla_angulos_poligonal(res: Resultado):
    filas = [["VÉRTICE", "ÁNG. MEDIDO", "CORRECCIÓN", "ÁNG. COMPENS.", "LADO", "AZIMUT",
              "DISTANCIA (m)"]]
    corr = -res.error_angular / res.n
    for i in range(res.n):
        filas.append([
            res.nombres[i], grados_a_gms(res.angulos_medidos[i]),
            grados_a_gms(corr, 1), grados_a_gms(res.angulos[i]),
            res.lados[i], grados_a_gms(res.azimuts[i]), fmt(res.distancias[i]),
        ])
    filas.append(["Σ", grados_a_gms(sum(res.angulos_medidos)), grados_a_gms(-res.error_angular, 1),
                  grados_a_gms(sum(res.angulos)), "", "", fmt(res.perimetro)])
    anchos = [1.5 * cm, 2.6 * cm, 2.3 * cm, 2.8 * cm, 1.8 * cm, 2.4 * cm]
    anchos.append(ANCHO_UTIL - sum(anchos))
    return _tabla(filas, anchos, alinear_derecha_desde=1, fila_total=True)


def tabla_heron(res: Resultado):
    mostrar_signo = any(t.signo < 0 for t in res.triangulos)
    cab = ["TRIÁNGULO", "a (m)", "b (m)", "c (m)", "s (m)", "ÁREA (m²)"]
    if mostrar_signo:
        cab.append("SIGNO")
    filas = [cab]
    for t in res.triangulos:
        fila = [t.nombre, fmt(t.a), fmt(t.b), fmt(t.c), fmt(t.s), fmt(t.area, 4)]
        if mostrar_signo:
            fila.append("+" if t.signo > 0 else "−")
        filas.append(fila)
    total = res.area_heron if res.area_heron is not None else sum(t.area for t in res.triangulos)
    fila_tot = ["TOTAL", "", "", "", "", fmt(total, 4)]
    if mostrar_signo:
        fila_tot.append("")
    filas.append(fila_tot)
    n_col = len(cab)
    ancho_col = (ANCHO_UTIL - 2.4 * cm) / (n_col - 1)
    return _tabla(filas, [2.4 * cm] + [ancho_col] * (n_col - 1), fila_total=True)


def tabla_gauss(res: Resultado):
    filas = [["i", "X i", "Y i", "X i · Y i+1", "X i+1 · Y i"]]
    s1 = s2 = Decimal(0)
    for i, ((x, y), (p1, p2)) in enumerate(zip(res.coords, res.productos)):
        filas.append([res.nombres[i], fmt(x), fmt(y), fmt(p1, 4), fmt(p2, 4)])
        s1 += p1
        s2 += p2
    filas.append(["Σ", "", "", fmt(s1, 4), fmt(s2, 4)])
    anchos = [1.4 * cm] + [(ANCHO_UTIL - 1.4 * cm) / 4] * 4
    return _tabla(filas, anchos, fila_total=True), s1, s2


# ---------------------------------------------------------------------------
# Cabecera y pie
# ---------------------------------------------------------------------------
def _dibujar_cabecera_pie(canvas, doc, datos):
    canvas.saveState()
    ancho, alto = A4

    x_logo, y_logo, w_logo, h_logo = 1.8 * cm, alto - 2.6 * cm, 2.8 * cm, 1.6 * cm
    if os.path.exists(RUTA_LOGO):
        img = ImageReader(RUTA_LOGO)
        iw, ih = img.getSize()
        aspecto = iw / ih
        if w_logo / h_logo > aspecto:
            h_d, w_d = h_logo, h_logo * aspecto
        else:
            w_d, h_d = w_logo, w_logo / aspecto
        canvas.drawImage(img, x_logo + (w_logo - w_d) / 2, y_logo + (h_logo - h_d) / 2,
                         width=w_d, height=h_d, mask="auto")

    canvas.setFont("Helvetica-Bold", 14)
    canvas.setFillColor(NEGRO)
    canvas.drawCentredString(ancho / 2, alto - 1.6 * cm, "REPORTE DE CÁLCULO DE ÁREA")
    canvas.setFont("Helvetica", 9.5)
    canvas.setFillColor(GRIS_TEXTO)
    canvas.drawCentredString(ancho / 2, alto - 2.15 * cm, "Polígono / Terreno — Matemática Aplicada")

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(ROJO)
    canvas.drawRightString(ancho - 1.8 * cm, alto - 1.6 * cm, datos.get("Código", ""))
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(NEGRO)
    canvas.drawRightString(ancho - 1.8 * cm, alto - 1.95 * cm, datos.get("Fecha", ""))

    canvas.setFillColor(ROJO)
    canvas.rect(1.8 * cm, alto - 2.85 * cm, ancho - 3.6 * cm, 0.09 * cm, stroke=0, fill=1)

    canvas.setStrokeColor(GRIS_MEDIO)
    canvas.setLineWidth(0.5)
    canvas.line(1.8 * cm, 2.0 * cm, ancho - 1.8 * cm, 2.0 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawString(1.8 * cm, 1.6 * cm,
                      "Producto académico — Topografía y Geodesia — Ciclo I — Matemática Aplicada")
    canvas.drawRightString(ancho - 1.8 * cm, 1.6 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# PDF principal
# ---------------------------------------------------------------------------
def generar_pdf(res: Resultado, datos: dict | None = None, ruta_salida=None) -> bytes:
    """
    Genera el reporte en PDF. Si `ruta_salida` es None devuelve los bytes del PDF.
    `datos` = diccionario con los datos del proyecto (Proyecto, Propietario, ...).
    """
    datos = dict(datos or {})
    datos.setdefault("Fecha", date.today().strftime("%d/%m/%Y"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        ruta_salida or buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=3.3 * cm, bottomMargin=2.4 * cm,
        title="Reporte de cálculo de área", author=datos.get("Elaborado por", ""),
    )

    story = []
    datos_tabla = {k: v for k, v in datos.items() if k not in ("Código",)}
    story += [_encabezado_seccion("1. DATOS DEL TERRENO"), Spacer(1, 4),
              tabla_datos_proyecto(datos_tabla), Spacer(1, 4),
              Paragraph(f"<b>Método de cálculo:</b> {NOMBRE_METODO[res.metodo]} &nbsp;·&nbsp; "
                        f"<b>N° de lados:</b> {res.n}", st_celda),
              Spacer(1, 10)]

    # --- Gráfico
    png = generar_grafico(res)
    ancho_img = ANCHO_UTIL
    alto_img = ancho_img * 5.4 / 7.0
    story += [KeepTogether([_encabezado_seccion("2. GRÁFICO DEL POLÍGONO"), Spacer(1, 4),
                            Image(io.BytesIO(png), width=ancho_img, height=alto_img)])]
    if not res.coords_dadas:
        story.append(Paragraph(
            "Nota: las coordenadas del gráfico son locales (vértice A en el origen y lado AB "
            "hacia el Norte o según el azimut inicial) y se obtuvieron a partir de las "
            "distancias ingresadas.", st_nota))
    story.append(Spacer(1, 10))

    # --- Cuadros de datos
    sec = 3
    if res.coords_dadas:
        story += _bloque(f"{sec}. CUADRO DE COORDENADAS", tabla_coordenadas(res))
        story.append(Spacer(1, 10))
        sec += 1
    elif res.metodo == "angulos":
        if math.isfinite(res.precision):
            nota_cierre = (f"Error angular: {grados_a_gms(res.error_angular, 1)} &nbsp;·&nbsp; "
                           f"Error de cierre lineal: {fmt(res.error_cierre_lineal, 4)} m "
                           f"&nbsp;·&nbsp; Precisión: 1/{res.precision:,.0f} &nbsp;·&nbsp; "
                           "Compensación: Bowditch")
        else:
            nota_cierre = (f"Error angular: {grados_a_gms(res.error_angular, 1)} &nbsp;·&nbsp; "
                           "Cierre lineal perfecto")
        story += [KeepTogether([
            _encabezado_seccion(f"{sec}. CUADRO DE LADOS, DISTANCIAS Y ÁNGULOS"), Spacer(1, 4),
            tabla_angulos_poligonal(res), Spacer(1, 4), Paragraph(nota_cierre, st_nota),
        ]), Spacer(1, 10)]
        sec += 1
        story += _bloque(f"{sec}. CUADRO DE COORDENADAS CALCULADAS (compensadas)",
                         tabla_coordenadas(res, "X (m)", "Y (m)"))
        story.append(Spacer(1, 10))
        sec += 1
    else:
        story += _bloque(f"{sec}. CUADRO DE LADOS Y DISTANCIAS", tabla_lados(res))
        story.append(Spacer(1, 10))
        sec += 1

    # --- Desarrollo del cálculo
    bloque = [_encabezado_seccion(f"{sec}. DESARROLLO DEL CÁLCULO"), Spacer(1, 6)]
    if res.metodo in ("coordenadas", "angulos"):
        tg, s1, s2 = tabla_gauss(res)
        bloque += [
            Paragraph("<b>Fórmula de Gauss (método de los determinantes):</b>", st_celda),
            Paragraph("A = ½ · | Σ (X<sub>i</sub> · Y<sub>i+1</sub>) − Σ (X<sub>i+1</sub> · "
                      "Y<sub>i</sub>) |", st_formula),
            Spacer(1, 4), tg, Spacer(1, 4),
            Paragraph(f"A = ½ · | {fmt(s1, 4)} − {fmt(s2, 4)} | = <b>{fmt(res.area, 4)} m²</b>",
                      st_formula),
            Spacer(1, 10),
        ]
        story.append(KeepTogether(bloque[:6]))
        story += bloque[6:]
        bloque = []
        titulo_heron = "<b>Verificación por triangulación desde el vértice " \
                       f"{res.nombres[0]} y fórmula de Herón:</b>"
    else:
        titulo_heron = "<b>Triangulación desde el vértice " \
                       f"{res.nombres[0]} y fórmula de Herón:</b>"
    bloque += [
        Paragraph(titulo_heron, st_celda),
        Paragraph("s = (a + b + c) / 2 &nbsp;&nbsp;&nbsp;&nbsp; "
                  "A = √[ s (s − a) (s − b) (s − c) ]", st_formula),
        Spacer(1, 4), tabla_heron(res),
    ]
    if any(t.signo < 0 for t in res.triangulos):
        bloque.append(Paragraph(
            "El polígono es no convexo: los triángulos con signo (−) quedan fuera del terreno y "
            "su área se resta.", st_nota))
    story += [KeepTogether(bloque), Spacer(1, 12)]

    # --- Avisos
    if res.avisos:
        story += [Paragraph("<b>Observaciones:</b> " + " ".join(res.avisos), st_nota),
                  Spacer(1, 8)]

    # --- Resultado
    res_tab = Table([
        [Paragraph("ÁREA DEL TERRENO", st_celda_b), Paragraph("PERÍMETRO", st_celda_b)],
        [Paragraph(f"{res.area:,.2f} m²<br/><font size=10>{res.area_ha:,.4f} ha</font>", st_area),
         Paragraph(f"{res.perimetro:,.2f} m", st_area)],
    ], colWidths=[ANCHO_UTIL * 0.6, ANCHO_UTIL * 0.4])
    res_tab.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, ROJO),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_MEDIO),
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_CLARO),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether([_encabezado_seccion(f"{sec + 1}. RESULTADO"), Spacer(1, 6),
                               res_tab]))

    doc.build(story,
              onFirstPage=lambda c, d: _dibujar_cabecera_pie(c, d, datos),
              onLaterPages=lambda c, d: _dibujar_cabecera_pie(c, d, datos))
    if ruta_salida:
        return b""
    return buf.getvalue()
