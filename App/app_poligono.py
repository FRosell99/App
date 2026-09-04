# -*- coding: utf-8 -*-
"""
App - Cálculo de Área y Ángulos de un Polígono de Terreno
Método de la cuerda (ángulos) + Triangulación con fórmula de Herón (área)
"""
import streamlit as st
import math
import os
from datetime import date
from itertools import combinations
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# MOTOR DE CÁLCULO
# ---------------------------------------------------------------------------
def angulo_por_cuerda(cuerda, r):
    ratio = cuerda / (2 * r)
    ratio = max(-1.0, min(1.0, ratio))
    return 2 * math.degrees(math.asin(ratio))


def grados_a_dms(angle_deg):
    sign = "-" if angle_deg < 0 else ""
    angle_deg = abs(angle_deg)
    d = int(angle_deg)
    m_full = (angle_deg - d) * 60
    m = int(m_full)
    s = (m_full - m) * 60
    return f"{sign}{d}°{m}'{s:.1f}\""


def calcular_todo(nombres, distancias_por_lado, cuerdas_por_vertice, radio, diagonales, azimut_inicial=0.0):
    n = len(nombres)
    lados_labels = [f"{nombres[i]}-{nombres[(i+1)%n]}" for i in range(n)]

    angulos_crudos = {v: angulo_por_cuerda(cuerdas_por_vertice[v], radio) for v in nombres}
    suma_cruda = sum(angulos_crudos.values())
    suma_teorica = (n - 2) * 180
    error_cierre = suma_teorica - suma_cruda
    compensacion = error_cierre / n
    angulos_comp = {v: angulos_crudos[v] + compensacion for v in nombres}

    edges = {}
    for i in range(n):
        key = frozenset({nombres[i], nombres[(i+1) % n]})
        edges[key] = distancias_por_lado[lados_labels[i]]
    for (v1, v2, dd) in diagonales:
        edges[frozenset({v1, v2})] = dd

    triangulos = []
    for combo in combinations(nombres, 3):
        a, b, c = combo
        e_ab, e_bc, e_ac = frozenset({a, b}), frozenset({b, c}), frozenset({a, c})
        if e_ab in edges and e_bc in edges and e_ac in edges:
            triangulos.append((a, b, c, edges[e_ab], edges[e_bc], edges[e_ac]))

    errores_triangulo = []
    area_total = 0.0
    for (a, b, c, la, lb, lc) in triangulos:
        ls = sorted([la, lb, lc])
        if ls[0] + ls[1] <= ls[2]:
            errores_triangulo.append(
                f"Triángulo {a}-{b}-{c}: lados {la:.3f} m, {lb:.3f} m, {lc:.3f} m no forman un triángulo válido "
                f"(la suma de los dos menores debe ser mayor que el mayor)."
            )
            continue
        s = (la + lb + lc) / 2
        area = math.sqrt(s * (s - la) * (s - lb) * (s - lc))
        area_total += area

    triangulacion_completa = (len(triangulos) == n - 2)

    azimuts = [None] * n
    azimuts[0] = azimut_inicial
    for i in range(1, n):
        interior_en_vi = angulos_comp[nombres[i]]
        azimuts[i] = (azimuts[i - 1] + 180 - interior_en_vi) % 360

    coords = {nombres[0]: (0.0, 0.0)}
    for i in range(n):
        v_a, v_b = nombres[i], nombres[(i + 1) % n]
        dist = distancias_por_lado[lados_labels[i]]
        az_rad = math.radians(azimuts[i])
        x0, y0 = coords[v_a]
        x1 = x0 + dist * math.sin(az_rad)
        y1 = y0 + dist * math.cos(az_rad)
        coords[v_b] = (x1, y1)

    x_cierre, y_cierre = coords[nombres[0]]
    error_lineal = math.hypot(x_cierre, y_cierre)

    return {
        "angulos_crudos": angulos_crudos,
        "suma_cruda": suma_cruda,
        "suma_teorica": suma_teorica,
        "error_cierre_angular": error_cierre,
        "compensacion_por_vertice": compensacion,
        "angulos_comp": angulos_comp,
        "lados_labels": lados_labels,
        "triangulos": triangulos,
        "errores_triangulo": errores_triangulo,
        "area_total": area_total,
        "triangulacion_completa": triangulacion_completa,
        "coords": coords,
        "error_lineal_cierre": error_lineal,
    }


def graficar_poligono(nombres, coords, angulos_comp, diagonales, area_total):
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    n = len(nombres)

    xs = [coords[nombres[i]][0] for i in range(n)] + [coords[nombres[0]][0]]
    ys = [coords[nombres[i]][1] for i in range(n)] + [coords[nombres[0]][1]]
    ax.plot(xs, ys, "-o", color="#C8102E", linewidth=2, markersize=6, zorder=3)

    for (v1, v2, dd) in diagonales:
        x1, y1 = coords[v1]
        x2, y2 = coords[v2]
        ax.plot([x1, x2], [y1, y2], "--", color="#1A1A1A", linewidth=1.1, zorder=2)

    for v in nombres:
        x, y = coords[v]
        etiqueta = f"{v}\n{grados_a_dms(angulos_comp[v])}"
        ax.annotate(etiqueta, (x, y), textcoords="offset points", xytext=(10, 8),
                    fontsize=8.5, fontweight="bold", color="#1A1A1A")
        ax.scatter([x], [y], color="#1A1A1A", s=25, zorder=4)

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(f"Polígono {'-'.join(nombres)}  —  Área: {area_total:.2f} m²",
                 fontsize=11, fontweight="bold", color="#1A1A1A")
    ax.set_xlabel("Este (m)")
    ax.set_ylabel("Norte (m)")
    ax.grid(True, linestyle=":", alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# INTERFAZ STREAMLIT
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Área y Ángulos de Polígono", page_icon="📐", layout="wide")

ruta_logo = os.path.join(os.path.dirname(__file__), "logo_sencico.png")
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    if os.path.exists(ruta_logo):
        st.image(ruta_logo, width=110)
with col_titulo:
    st.title("📐 Área y Ángulos de un Polígono de Terreno")
    st.caption("Método de la cuerda (ángulos) + Triangulación con fórmula de Herón (área)")

st.header("Datos generales")
c1, c2, c3 = st.columns(3)
with c1:
    cuadrilla = st.text_input("Nombre de la cuadrilla")
with c2:
    proyecto = st.text_input("Nombre del proyecto")
with c3:
    fecha = st.date_input("Fecha", value=date.today())

st.divider()

st.header("1. Configuración del polígono")
n = st.selectbox("Número de lados", [4, 5, 6])
n_diagonales = n - 3
st.caption(f"Un polígono de {n} lados necesita exactamente **{n_diagonales} diagonal(es)** para completar la triangulación.")

st.subheader("Nombres de los vértices")
default_names = ["A", "B", "C", "D", "E", "F"]
nombres = []
cols_nombres = st.columns(n)
for i in range(n):
    with cols_nombres[i]:
        nombre = st.text_input(f"Vértice {i+1}", value=default_names[i], key=f"nombre_v{i}")
    nombres.append(nombre.strip() or default_names[i])

if len(set(nombres)) != n:
    st.error("Los nombres de los vértices deben ser distintos entre sí.")
    st.stop()

st.subheader("Orientación de partida")
tiene_azimut = st.radio("¿Tienes un azimut real de campo para el primer lado?", ["No", "Sí"], horizontal=True)
if tiene_azimut == "Sí":
    azimut_inicial = st.number_input(
        f"Azimut real del lado {nombres[0]}-{nombres[1]} (grados decimales, 0-360, medido desde el Norte)",
        min_value=0.0, max_value=360.0, value=0.0, step=0.1,
    )
else:
    azimut_inicial = 0.0
    st.caption(f"Se asumirá el vértice {nombres[0]} en (0,0) con orientación de referencia 0° (Norte).")

st.subheader("Radio (r) usado para las cuerdas")
radio = st.number_input("Radio r (m)", min_value=0.0001, value=1.0, step=0.1, format="%.4f")

st.divider()

st.header("2. Tabla de mediciones por vértice")
st.caption("Ingresa la distancia de cada lado (hacia el siguiente vértice) y la cuerda medida en ese vértice.")

distancias = {}
cuerdas = {}
lados_labels = []

encabezados = st.columns([1, 1.5, 1.7, 1.7])
encabezados[0].markdown("**Vértice**")
encabezados[1].markdown("**Lado**")
encabezados[2].markdown("**Distancia (m)**")
encabezados[3].markdown("**Cuerda (m)**")

for i in range(n):
    v_actual = nombres[i]
    v_siguiente = nombres[(i + 1) % n]
    lado_label = f"{v_actual}-{v_siguiente}"
    lados_labels.append(lado_label)

    c1, c2, c3, c4 = st.columns([1, 1.5, 1.7, 1.7])
    with c1:
        st.markdown(f"**{v_actual}**")
    with c2:
        st.markdown(lado_label)
    with c3:
        d = st.number_input("Distancia", min_value=0.0, key=f"dist_{i}", label_visibility="collapsed")
    with c4:
        cu = st.number_input("Cuerda", min_value=0.0, key=f"cuerda_{i}", label_visibility="collapsed")
    distancias[lado_label] = d
    cuerdas[v_actual] = cu

st.divider()

st.header("3. Diagonales para la triangulación")
diagonales = []
if n_diagonales > 0:
    for i in range(n_diagonales):
        c1, c2, c3 = st.columns(3)
        with c1:
            v1 = st.selectbox(f"Vértice origen (diagonal {i+1})", nombres, key=f"diag_v1_{i}")
        with c2:
            idx_v1 = nombres.index(v1)
            adyacentes = {nombres[(idx_v1 - 1) % n], nombres[(idx_v1 + 1) % n]}
            opciones_destino = [v for v in nombres if v != v1]
            no_adyacentes = [v for v in opciones_destino if v not in adyacentes]
            default_idx = opciones_destino.index(no_adyacentes[0]) if no_adyacentes else 0
            v2 = st.selectbox(f"Vértice destino (diagonal {i+1})", opciones_destino,
                               index=default_idx, key=f"diag_v2_{i}")
        with c3:
            dd = st.number_input(f"Distancia diagonal {i+1} (m)", min_value=0.0, key=f"diag_d_{i}")
        diagonales.append((v1, v2, dd))

st.divider()

# ---------------------------------------------------------------------------
# CÁLCULO
# ---------------------------------------------------------------------------
if st.button("🧮 Calcular área y ángulos", type="primary"):
    if any(distancias[l] <= 0 for l in lados_labels) or any(cuerdas[v] <= 0 for v in nombres):
        st.error("Todas las distancias y cuerdas deben ser mayores a 0.")
        st.stop()
    if n_diagonales > 0 and any(dd[2] <= 0 for dd in diagonales):
        st.error("Todas las distancias de diagonales deben ser mayores a 0.")
        st.stop()

    lados_existentes = {frozenset({nombres[i], nombres[(i + 1) % n]}) for i in range(n)}
    diagonales_invalidas = [
        (v1, v2) for (v1, v2, _) in diagonales if frozenset({v1, v2}) in lados_existentes
    ]
    if diagonales_invalidas:
        st.error(
            "⚠️ Una diagonal no puede unir dos vértices adyacentes (ya conectados por un lado del polígono): "
            + ", ".join(f"{v1}-{v2}" for v1, v2 in diagonales_invalidas)
            + ". Elige vértices no adyacentes para cada diagonal."
        )
        st.stop()

    if len({frozenset({v1, v2}) for v1, v2, _ in diagonales}) != len(diagonales):
        st.error("⚠️ Hay diagonales repetidas (la misma pareja de vértices seleccionada más de una vez).")
        st.stop()

    resultado = calcular_todo(nombres, distancias, cuerdas, radio, diagonales, azimut_inicial)

    if resultado["errores_triangulo"]:
        st.error("⚠️ Se encontraron triángulos inválidos — revisa los datos de campo:")
        for err in resultado["errores_triangulo"]:
            st.write(f"- {err}")
        st.stop()

    if not resultado["triangulacion_completa"]:
        st.warning(
            f"La triangulación no está completa: se esperaban {n-2} triángulos y se encontraron "
            f"{len(resultado['triangulos'])}. Revisa que las diagonales conecten correctamente el polígono."
        )

    st.success("Cálculo realizado correctamente.")

    # --- Datos generales en el resultado ---
    st.subheader("Datos del levantamiento")
    r1, r2, r3 = st.columns(3)
    r1.markdown(f"**Cuadrilla:** {cuadrilla or '—'}")
    r2.markdown(f"**Proyecto:** {proyecto or '—'}")
    r3.markdown(f"**Fecha:** {fecha.strftime('%d/%m/%Y')}")

    # --- Texto de compensación ---
    st.subheader("Verificación y compensación angular")
    err = resultado["error_cierre_angular"]
    comp = resultado["compensacion_por_vertice"]
    st.info(
        f"Suma de ángulos medidos: **{resultado['suma_cruda']:.4f}°** — "
        f"Suma teórica esperada ({n}-2)×180° = **{resultado['suma_teorica']}°**.\n\n"
        f"**Error de cierre angular: {grados_a_dms(err)} ({err:.4f}°)**.\n\n"
        f"Se aplicó una compensación de **{grados_a_dms(comp)} ({comp:.4f}°)** en cada uno de los {n} vértices "
        f"para cerrar el polígono antes de graficarlo."
    )
    if resultado["error_lineal_cierre"] > 0.001:
        st.caption(
            f"Nota: persiste un pequeño error lineal de cierre de {resultado['error_lineal_cierre']:.4f} m, "
            "atribuible a la precisión de las distancias medidas (no corregido en esta versión)."
        )

    # --- Tabla de resultados ---
    st.subheader("Tabla de resultados")
    filas = []
    for i in range(n):
        v = nombres[i]
        filas.append({
            "Vértice": v,
            "Lado": lados_labels[i],
            "Distancia (m)": f"{distancias[lados_labels[i]]:.3f}",
            "Ángulo": grados_a_dms(resultado["angulos_comp"][v]),
        })
    st.table(filas)

    # --- Área ---
    st.subheader("Área total")
    st.metric("Área del polígono", f"{resultado['area_total']:.2f} m²")

    # --- Gráfico ---
    st.subheader("Representación gráfica")
    fig = graficar_poligono(nombres, resultado["coords"], resultado["angulos_comp"], diagonales, resultado["area_total"])
    st.pyplot(fig)