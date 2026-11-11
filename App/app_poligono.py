# -*- coding: utf-8 -*-
"""
App - Cálculo de áreas de polígonos (terrenos)
Curso: Matemática Aplicada — Topografía y Geodesia (Ciclo I) — SENCICO

Permite ingresar:
  1. Coordenadas (Este, Norte) de los n vértices  -> Fórmula de Gauss + verificación con Herón
  2. Lados y distancias (y diagonales si n > 3)   -> Triangulación + fórmula de Herón
  3. Lados, distancias y ángulos internos          -> Poligonal cerrada compensada + Gauss

y genera un reporte PDF con el gráfico del polígono, el cuadro de coordenadas y/o
el cuadro de lados y distancias, el desarrollo del cálculo y el área del terreno.

Ejecutar con:   streamlit run app_poligono.py
"""
from datetime import date

import pandas as pd
import streamlit as st

import poligono_calculos as pc
import poligono_reporte as pr

MODO_COORD = "Coordenadas (Este, Norte)"
MODO_LADOS = "Lados y distancias (Herón)"
MODO_ANG = "Lados, distancias y ángulos internos"

EJEMPLOS = {
    MODO_COORD: {
        "n": 5,
        "tabla": [("A", 285430.25, 8645120.40), ("B", 285480.10, 8645135.75),
                  ("C", 285495.60, 8645090.30), ("D", 285470.00, 8645060.00),
                  ("E", 285438.90, 8645075.20)],
    },
    MODO_LADOS: {"n": 4, "lados": [52.30, 47.80, 39.50, 41.20], "diagonales": [65.40]},
    MODO_ANG: {"n": 4, "lados": [30.02, 50.00, 29.99, 50.01],
               "angulos": [(90, 0, 36), (89, 59, 24), (90, 1, 12), (90, 0, 0)]},
}

st.set_page_config(page_title="Área de Polígonos", page_icon="📐", layout="wide")


# ---------------------------------------------------------------------------
# Utilidades de la interfaz
# ---------------------------------------------------------------------------
def _vacio(x) -> bool:
    return x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, str) and not x.strip())


def _num(x):
    if _vacio(x):
        return None
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def _tabla_inicial(modo: str, n: int, usar_ejemplo: bool) -> pd.DataFrame:
    nombres = pc.nombres_vertices(n)
    ej = EJEMPLOS[modo] if usar_ejemplo and EJEMPLOS[modo]["n"] == n else None
    if modo == MODO_COORD:
        if ej:
            filas = ej["tabla"]
        else:
            filas = [(nombres[i], None, None) for i in range(n)]
        return pd.DataFrame(filas, columns=["Vértice", "Este (m)", "Norte (m)"]).astype(
            {"Este (m)": "float64", "Norte (m)": "float64"})
    lados = pc.nombres_lados(nombres)
    if modo == MODO_LADOS:
        dist = ej["lados"] if ej else [None] * n
        return pd.DataFrame({"Lado": lados, "Distancia (m)": dist}).astype(
            {"Distancia (m)": "float64"})
    # MODO_ANG
    dist = ej["lados"] if ej else [None] * n
    angs = ej["angulos"] if ej else [(None, None, None)] * n
    return pd.DataFrame({
        "Vértice": nombres,
        "Grados": [a[0] for a in angs],
        "Minutos": [a[1] for a in angs],
        "Segundos": [a[2] for a in angs],
        "Lado": lados,
        "Distancia (m)": dist,
    }).astype({"Grados": "float64", "Minutos": "float64", "Segundos": "float64",
               "Distancia (m)": "float64"})


def _tabla_diagonales(n: int, usar_ejemplo: bool) -> pd.DataFrame:
    nombres = pc.nombres_vertices(n)
    ej = EJEMPLOS[MODO_LADOS]
    dist = ej["diagonales"] if usar_ejemplo and ej["n"] == n else [None] * (n - 3)
    return pd.DataFrame({
        "Diagonal": [f"{nombres[0]}-{nombres[k]}" for k in range(2, n - 1)],
        "Distancia (m)": dist,
    }).astype({"Distancia (m)": "float64"})


def _mostrar_resultado(res: pc.Resultado):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Área", f"{res.area:,.2f} m²")
    c2.metric("Área", f"{res.area_ha:,.4f} ha")
    c3.metric("Perímetro", f"{res.perimetro:,.2f} m")
    c4.metric("N° de lados", res.n)

    for aviso in res.avisos:
        st.warning(aviso)

    col_g, col_t = st.columns([1.15, 1])
    with col_g:
        st.image(pr.generar_grafico(res, dpi=150), width="stretch")
    with col_t:
        if res.coords_dadas or res.metodo == "angulos":
            st.markdown("**Cuadro de coordenadas**" +
                        (" (calculadas y compensadas)" if res.metodo == "angulos" else ""))
            st.dataframe(pd.DataFrame({
                "Vértice": res.nombres,
                "Lado": res.lados,
                "Distancia (m)": [round(d, 3) for d in res.distancias],
                "Áng. interno": [pc.grados_a_gms(a) for a in res.angulos] if res.angulos
                else ["—"] * res.n,
                "Azimut": [pc.grados_a_gms(a) for a in res.azimuts],
                "Este / X (m)": [round(p[0], 3) for p in res.coords],
                "Norte / Y (m)": [round(p[1], 3) for p in res.coords],
            }), hide_index=True, width="stretch")
        else:
            st.markdown("**Cuadro de lados y distancias**")
            st.dataframe(pd.DataFrame({
                "Lado": res.lados,
                "Distancia (m)": [round(d, 3) for d in res.distancias],
                "Áng. interno": [f"{res.nombres[i]}: {pc.grados_a_gms(a)}"
                                 for i, a in enumerate(res.angulos)] if res.angulos
                else ["—"] * res.n,
            }), hide_index=True, width="stretch")
            if res.diagonales:
                st.dataframe(pd.DataFrame(res.diagonales, columns=["Diagonal", "Distancia (m)"]),
                             hide_index=True, width="stretch")

        if res.metodo == "angulos":
            prec = f"1/{res.precision:,.0f}" if res.precision != float("inf") else "perfecta"
            st.caption(f"Error angular: {pc.grados_a_gms(res.error_angular, 1)} · "
                       f"Error de cierre lineal: {res.error_cierre_lineal:.4f} m · "
                       f"Precisión: {prec} · Compensación: Bowditch")

    with st.expander("📘 Desarrollo del cálculo", expanded=False):
        if res.metodo in ("coordenadas", "angulos"):
            st.markdown("**Fórmula de Gauss (determinantes)**")
            st.latex(r"A=\frac{1}{2}\left|\sum_{i=1}^{n}\left(X_i\,Y_{i+1}-X_{i+1}\,Y_i\right)\right|")
            s1 = sum(p[0] for p in res.productos)
            s2 = sum(p[1] for p in res.productos)
            st.dataframe(pd.DataFrame({
                "i": res.nombres,
                "Xi": [p[0] for p in res.coords],
                "Yi": [p[1] for p in res.coords],
                "Xi·Yi+1": [float(p[0]) for p in res.productos],
                "Xi+1·Yi": [float(p[1]) for p in res.productos],
            }), hide_index=True, width="stretch")
            st.markdown(f"A = ½ · | {s1:,.4f} − {s2:,.4f} | = **{res.area:,.4f} m²**")
            st.markdown(f"**Verificación con Herón** (triangulación desde el vértice {res.nombres[0]})")
        else:
            st.markdown(f"**Triangulación desde el vértice {res.nombres[0]} y fórmula de Herón**")
        st.latex(r"s=\frac{a+b+c}{2}\qquad A=\sqrt{s(s-a)(s-b)(s-c)}")
        st.dataframe(pd.DataFrame({
            "Triángulo": [t.nombre for t in res.triangulos],
            "a (m)": [t.a for t in res.triangulos],
            "b (m)": [t.b for t in res.triangulos],
            "c (m)": [t.c for t in res.triangulos],
            "s (m)": [t.s for t in res.triangulos],
            "Área (m²)": [t.area for t in res.triangulos],
            "Signo": ["+" if t.signo > 0 else "−" for t in res.triangulos],
        }), hide_index=True, width="stretch")
        st.markdown(f"Σ áreas = **{res.area_heron:,.4f} m²**")
        if any(t.signo < 0 for t in res.triangulos):
            st.caption("Polígono no convexo: los triángulos con signo (−) quedan fuera del "
                       "terreno y se restan.")


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------
st.title("📐 Cálculo de Área de Polígonos")
st.caption("Matemática Aplicada · Topografía y Geodesia · Ciclo I — Fórmula de Herón, "
           "fórmula de Gauss y triangulación, con reporte en PDF")

# 1. Datos del terreno -------------------------------------------------------
st.header("1. Datos del terreno")
c1, c2, c3 = st.columns(3)
with c1:
    proyecto = st.text_input("Proyecto / Terreno", placeholder="Ej.: Lote 12, Mz. B")
    propietario = st.text_input("Propietario")
with c2:
    ubicacion = st.text_input("Ubicación (distrito / provincia)")
    elaborado = st.text_input("Elaborado por")
with c3:
    codigo = st.text_input("Código del reporte", value="REP-2026-001")
    fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")

st.divider()

# 2. Datos del polígono --------------------------------------------------------
st.header("2. Datos del polígono")
cm1, cm2, cm3 = st.columns([2.2, 1, 1])
with cm1:
    modo = st.radio("¿Qué datos tiene del terreno?", [MODO_COORD, MODO_LADOS, MODO_ANG],
                    horizontal=True)


def _cargar_ejemplo(m):
    st.session_state["ejemplo"] = m
    st.session_state["n"] = EJEMPLOS[m]["n"]


with cm2:
    st.session_state.setdefault("n", 4)
    n = int(st.number_input("Número de lados (n)", min_value=3, max_value=60, step=1, key="n"))
with cm3:
    st.write("")
    st.button("Cargar ejemplo", help="Rellena la tabla con un ejemplo resuelto",
              on_click=_cargar_ejemplo, args=(modo,))

usar_ejemplo = st.session_state.get("ejemplo") == modo and n == EJEMPLOS[modo]["n"]

clave = f"{modo}-{n}-{usar_ejemplo}"
datos_ok = False
res = None
errores = []

if modo == MODO_COORD:
    st.markdown("Ingrese las coordenadas de los vértices **en orden**, recorriendo el perímetro "
                "(sentido horario o antihorario). Puede pegar los datos desde Excel.")
    tabla = st.data_editor(_tabla_inicial(modo, n, usar_ejemplo), key=f"t-{clave}",
                           num_rows="fixed", hide_index=True, width="stretch",
                           column_config={
                               "Vértice": st.column_config.TextColumn(width="small"),
                               "Este (m)": st.column_config.NumberColumn(format="%.3f"),
                               "Norte (m)": st.column_config.NumberColumn(format="%.3f"),
                           })
    nombres = [str(v).strip() if not _vacio(v) else pc.nombre_vertice(i)
               for i, v in enumerate(tabla["Vértice"])]
    coords = [(_num(e), _num(nn)) for e, nn in zip(tabla["Este (m)"], tabla["Norte (m)"])]
    if all(x is not None and y is not None for x, y in coords):
        try:
            res = pc.calcular_por_coordenadas(coords, nombres)
        except pc.ErrorDatos as e:
            errores.append(str(e))

elif modo == MODO_LADOS:
    if n == 3:
        st.markdown("Para un **triángulo** basta con ingresar sus tres lados: el área se obtiene "
                    "directamente con la **fórmula de Herón**.")
    else:
        st.markdown(
            f"Un polígono de {n} lados no queda definido solo con sus lados. Se divide en "
            f"**{n - 2} triángulos** trazando **{n - 3} diagonal(es) desde el vértice A** y se "
            "aplica la **fórmula de Herón** a cada triángulo.")
    cl, cd = st.columns(2) if n > 3 else (st.container(), None)
    with cl:
        st.markdown("**Lados**")
        tabla = st.data_editor(_tabla_inicial(modo, n, usar_ejemplo), key=f"t-{clave}",
                               num_rows="fixed", hide_index=True, width="stretch",
                               disabled=["Lado"],
                               column_config={"Distancia (m)": st.column_config.NumberColumn(
                                   format="%.3f", min_value=0.0)})
    diagonales = []
    if n > 3:
        with cd:
            st.markdown("**Diagonales desde el vértice A**")
            tabla_d = st.data_editor(_tabla_diagonales(n, usar_ejemplo), key=f"d-{clave}",
                                     num_rows="fixed", hide_index=True, width="stretch",
                                     disabled=["Diagonal"],
                                     column_config={"Distancia (m)": st.column_config.NumberColumn(
                                         format="%.3f", min_value=0.0)})
            diagonales = [_num(d) for d in tabla_d["Distancia (m)"]]
    lados = [_num(d) for d in tabla["Distancia (m)"]]
    if all(v is not None for v in lados + diagonales):
        try:
            res = pc.calcular_por_lados(lados, diagonales)
        except pc.ErrorDatos as e:
            errores.append(str(e))

else:  # MODO_ANG
    st.markdown("Ingrese el **ángulo interno** medido en cada vértice y la **distancia** de cada "
                "lado. Se verifica la suma de ángulos (n − 2)·180°, se compensa el error angular, "
                "se calculan azimuts y coordenadas (compensación de Bowditch) y luego el área.")
    o1, o2, o3, o4 = st.columns(4)
    with o1:
        sentido = st.radio("Sentido de recorrido", ["horario", "antihorario"], horizontal=True)
    with o2:
        st.markdown("Azimut del lado A-B")
        a1, a2, a3 = st.columns(3)
        az_g = a1.number_input("°", 0, 359, 0, key="azg")
        az_m = a2.number_input("'", 0, 59, 0, key="azm")
        az_s = a3.number_input('"', 0.0, 59.99, 0.0, key="azs")
    with o3:
        x0 = st.number_input("X / Este de A (m)", value=0.0, format="%.3f")
    with o4:
        y0 = st.number_input("Y / Norte de A (m)", value=0.0, format="%.3f")
    tabla = st.data_editor(_tabla_inicial(modo, n, usar_ejemplo), key=f"t-{clave}",
                           num_rows="fixed", hide_index=True, width="stretch",
                           disabled=["Vértice", "Lado"],
                           column_config={
                               "Grados": st.column_config.NumberColumn(min_value=0, max_value=359,
                                                                       step=1, format="%d°"),
                               "Minutos": st.column_config.NumberColumn(min_value=0, max_value=59,
                                                                        step=1, format="%d'"),
                               "Segundos": st.column_config.NumberColumn(min_value=0.0,
                                                                         max_value=59.99,
                                                                         format='%.1f"'),
                               "Distancia (m)": st.column_config.NumberColumn(format="%.3f",
                                                                              min_value=0.0),
                           })
    lados = [_num(d) for d in tabla["Distancia (m)"]]
    grados = [_num(g) for g in tabla["Grados"]]
    if all(v is not None for v in lados + grados):
        angulos = [pc.gms_a_grados(g, _num(m) or 0.0, _num(s) or 0.0)
                   for g, m, s in zip(grados, tabla["Minutos"], tabla["Segundos"])]
        st.caption(f"Σ ángulos medidos = {pc.grados_a_gms(sum(angulos))} · "
                   f"Σ teórica = (n − 2)·180° = {(n - 2) * 180}°")
        try:
            res = pc.calcular_por_angulos(lados, angulos, pc.gms_a_grados(az_g, az_m, az_s),
                                          (x0, y0), sentido=sentido)
        except pc.ErrorDatos as e:
            errores.append(str(e))

for e in errores:
    st.error(e)

st.divider()

# 3. Resultados -----------------------------------------------------------------
st.header("3. Resultados")
if res is None:
    if not errores:
        st.info("Complete todos los datos de la tabla para calcular el área.")
else:
    _mostrar_resultado(res)

    st.divider()
    st.header("4. Reporte PDF")
    datos = {
        "Proyecto": proyecto or "—",
        "Propietario": propietario or "—",
        "Ubicación": ubicacion or "—",
        "Elaborado por": elaborado or "—",
        "Fecha": fecha.strftime("%d/%m/%Y"),
        "Código": codigo,
    }
    if st.button("📄 Generar reporte PDF", type="primary"):
        with st.spinner("Generando reporte..."):
            st.session_state["pdf"] = pr.generar_pdf(res, datos)
            st.session_state["pdf_clave"] = (clave, repr(res.coords), repr(datos))
    if st.session_state.get("pdf_clave") == (clave, repr(res.coords), repr(datos)):
        st.success("Reporte generado correctamente.")
        nombre = (proyecto or "terreno").strip().replace(" ", "_")
        st.download_button("⬇️ Descargar PDF", data=st.session_state["pdf"],
                           file_name=f"Reporte_Area_{nombre}.pdf", mime="application/pdf")
