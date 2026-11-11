# -*- coding: utf-8 -*-
"""
Cálculos geométricos para el área de polígonos (terrenos).

Métodos implementados
---------------------
1. Coordenadas (E, N)  -> Fórmula de Gauss / método de los determinantes
   (fórmula del "cordón de zapato"):
        A = 1/2 * | Σ (x_i * y_(i+1) - x_(i+1) * y_i) |
   Como verificación se descompone el polígono en triángulos desde el
   vértice 1 y se aplica la fórmula de Herón a cada uno.

2. Lados y diagonales  -> Triangulación + fórmula de Herón:
        s = (a + b + c) / 2
        A = sqrt( s (s - a) (s - b) (s - c) )
   Para n = 3 basta con los tres lados. Para n > 3 se necesitan las
   (n - 3) diagonales trazadas desde el vértice 1.

3. Lados y ángulos internos -> Poligonal cerrada: se compensa el error
   angular, se calculan azimuts, proyecciones y coordenadas (compensación
   de Bowditch) y finalmente se aplica la fórmula de Gauss.

Todas las funciones trabajan en metros y grados sexagesimales.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def nombre_vertice(i: int) -> str:
    """0 -> 'A', 1 -> 'B', ..., 25 -> 'Z', 26 -> 'A1', ..."""
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if i < 26:
        return letras[i]
    return f"{letras[i % 26]}{i // 26}"


def nombres_vertices(n: int) -> list[str]:
    return [nombre_vertice(i) for i in range(n)]


def nombres_lados(nombres: list[str]) -> list[str]:
    n = len(nombres)
    return [f"{nombres[i]}-{nombres[(i + 1) % n]}" for i in range(n)]


def distancia(p, q) -> float:
    return math.hypot(q[0] - p[0], q[1] - p[1])


def azimut(p, q) -> float:
    """Azimut (desde el Norte, sentido horario) de p hacia q, en grados [0, 360)."""
    az = math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
    return az % 360.0


def grados_a_gms(grados: float, decimales: int = 0) -> str:
    """Convierte grados decimales a texto  G° M' S\"."""
    signo = "-" if grados < 0 else ""
    g = abs(grados)
    d = int(g)
    m_total = (g - d) * 60
    m = int(m_total)
    s = round((m_total - m) * 60, decimales)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    s_txt = f"{s:0{3 + decimales if decimales else 2}.{decimales}f}"
    return f"{signo}{d}°{m:02d}'{s_txt}\""


def gms_a_grados(g: float, m: float = 0.0, s: float = 0.0) -> float:
    signo = -1 if g < 0 else 1
    return signo * (abs(g) + m / 60.0 + s / 3600.0)


class ErrorDatos(ValueError):
    """Error de validación de los datos de entrada."""


# ---------------------------------------------------------------------------
# Fórmula de Herón
# ---------------------------------------------------------------------------
@dataclass
class TrianguloHeron:
    nombre: str
    a: float
    b: float
    c: float
    s: float
    area: float
    signo: int = 1  # +1 o -1 (solo relevante para polígonos no convexos)


def heron(a: float, b: float, c: float, nombre: str = "") -> TrianguloHeron:
    """Área de un triángulo a partir de sus tres lados (fórmula de Herón)."""
    for lado in (a, b, c):
        if lado is None or lado <= 0:
            raise ErrorDatos(f"Triángulo {nombre}: todos los lados deben ser mayores que cero.")
    lados = sorted((a, b, c))
    tol = 1e-9 * max(lados)
    if lados[0] + lados[1] < lados[2] - tol:
        raise ErrorDatos(
            f"Triángulo {nombre}: los lados {a:.3f}, {b:.3f} y {c:.3f} no cumplen la "
            "desigualdad triangular (la suma de dos lados debe ser mayor que el tercero)."
        )
    s = (a + b + c) / 2.0
    prod = s * (s - a) * (s - b) * (s - c)
    area = math.sqrt(max(prod, 0.0))
    return TrianguloHeron(nombre, a, b, c, s, area)


# ---------------------------------------------------------------------------
# Fórmula de Gauss (determinantes / shoelace)
# ---------------------------------------------------------------------------
def _dec(x) -> Decimal:
    # str() da la representación decimal más corta del número ingresado,
    # así los productos de coordenadas UTM grandes se calculan sin redondeo.
    return Decimal(str(float(x)))


def productos_gauss(coords):
    """Filas (x_i*y_(i+1), x_(i+1)*y_i) calculadas en aritmética decimal exacta."""
    n = len(coords)
    filas = []
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        filas.append((_dec(x1) * _dec(y2), _dec(x2) * _dec(y1)))
    return filas


def area_gauss_con_signo(coords) -> float:
    """Área con signo (+ antihorario, - horario) por la fórmula de Gauss."""
    suma = sum((a - b for a, b in productos_gauss(coords)), Decimal(0))
    return float(suma / 2)


def _segmentos_se_cruzan(p1, p2, p3, p4) -> bool:
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)

    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    return o1 * o2 < 0 and o3 * o4 < 0


def es_poligono_simple(coords) -> bool:
    """True si ningún par de lados no consecutivos se cruza."""
    n = len(coords)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            if _segmentos_se_cruzan(coords[i], coords[(i + 1) % n],
                                    coords[j], coords[(j + 1) % n]):
                return False
    return True


def es_convexo(coords) -> bool:
    n = len(coords)
    signo = 0
    for i in range(n):
        a, b, c = coords[i], coords[(i + 1) % n], coords[(i + 2) % n]
        cruz = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cruz) < 1e-12:
            continue
        s = 1 if cruz > 0 else -1
        if signo == 0:
            signo = s
        elif s != signo:
            return False
    return True


def angulos_internos(coords) -> list[float]:
    """Ángulo interno en cada vértice (grados), válido para polígonos simples."""
    n = len(coords)
    antihorario = area_gauss_con_signo(coords) > 0
    angulos = []
    for i in range(n):
        prev, act, sig = coords[i - 1], coords[i], coords[(i + 1) % n]
        v1 = (prev[0] - act[0], prev[1] - act[1])
        v2 = (sig[0] - act[0], sig[1] - act[1])
        ang = math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                      v1[0] * v2[0] + v1[1] * v2[1]))
        # ang = ángulo girando de v1 a v2 en sentido antihorario
        ang = ang % 360.0
        if antihorario:
            ang = 360.0 - ang
        angulos.append(ang if ang != 0 else 360.0)
    # Normalización: para recorrido antihorario el interior queda a la izquierda.
    return angulos


# ---------------------------------------------------------------------------
# Resultado común
# ---------------------------------------------------------------------------
@dataclass
class Resultado:
    metodo: str                       # "coordenadas" | "triangulacion" | "angulos"
    nombres: list[str]
    coords: list[tuple[float, float]]  # coordenadas (dadas o calculadas) para el gráfico
    lados: list[str]
    distancias: list[float]
    area: float
    perimetro: float
    angulos: list[float] = field(default_factory=list)
    azimuts: list[float] = field(default_factory=list)
    triangulos: list[TrianguloHeron] = field(default_factory=list)
    diagonales: list[tuple[str, float]] = field(default_factory=list)
    productos: list[tuple[float, float]] = field(default_factory=list)
    area_heron: float | None = None
    convexo: bool = True
    simple: bool = True
    coords_dadas: bool = False
    avisos: list[str] = field(default_factory=list)
    # Solo para el método de ángulos
    error_angular: float | None = None
    angulos_medidos: list[float] = field(default_factory=list)
    error_cierre_lineal: float | None = None
    precision: float | None = None
    coords_sin_compensar: list[tuple[float, float]] = field(default_factory=list)

    @property
    def area_ha(self) -> float:
        return self.area / 10_000.0

    @property
    def n(self) -> int:
        return len(self.nombres)


def _triangulacion_desde_v1(coords, nombres):
    """Triángulos (V1, Vk, Vk+1) con Herón y signo según orientación."""
    triangulos = []
    for k in range(1, len(coords) - 1):
        p0, p1, p2 = coords[0], coords[k], coords[k + 1]
        a, b, c = distancia(p0, p1), distancia(p1, p2), distancia(p2, p0)
        t = heron(a, b, c, f"{nombres[0]}{nombres[k]}{nombres[k + 1]}")
        cruz = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
        t.signo = 1 if cruz >= 0 else -1
        triangulos.append(t)
    return triangulos


# ---------------------------------------------------------------------------
# Método 1: coordenadas
# ---------------------------------------------------------------------------
def calcular_por_coordenadas(coords, nombres=None) -> Resultado:
    coords = [(float(x), float(y)) for x, y in coords]
    n = len(coords)
    if n < 3:
        raise ErrorDatos("Se necesitan al menos 3 vértices.")
    nombres = list(nombres) if nombres else nombres_vertices(n)

    for i in range(n):
        for j in range(i + 1, n):
            if distancia(coords[i], coords[j]) < 1e-9:
                raise ErrorDatos(f"Los vértices {nombres[i]} y {nombres[j]} tienen las mismas coordenadas.")

    area_signo = area_gauss_con_signo(coords)
    if abs(area_signo) < 1e-9:
        raise ErrorDatos("Los puntos son colineales: el área es cero.")

    avisos = []
    simple = es_poligono_simple(coords)
    if not simple:
        avisos.append("Los lados del polígono se cruzan entre sí. Verifique el orden de los "
                      "vértices: deben ingresarse recorriendo el perímetro (horario o antihorario).")

    distancias = [distancia(coords[i], coords[(i + 1) % n]) for i in range(n)]
    azs = [azimut(coords[i], coords[(i + 1) % n]) for i in range(n)]
    triangulos = _triangulacion_desde_v1(coords, nombres)
    # Si el recorrido es horario, los signos se invierten para que el área sea positiva
    orient = 1 if area_signo > 0 else -1
    for t in triangulos:
        t.signo *= orient
    area_heron = abs(sum(t.signo * t.area for t in triangulos))
    convexo = es_convexo(coords)

    diagonales = [(f"{nombres[0]}-{nombres[k]}", distancia(coords[0], coords[k]))
                  for k in range(2, n - 1)]

    return Resultado(
        metodo="coordenadas",
        nombres=nombres,
        coords=coords,
        lados=nombres_lados(nombres),
        distancias=distancias,
        area=abs(area_signo),
        perimetro=sum(distancias),
        angulos=angulos_internos(coords) if simple else [],
        azimuts=azs,
        triangulos=triangulos,
        diagonales=diagonales,
        productos=productos_gauss(coords),
        area_heron=area_heron,
        convexo=convexo,
        simple=simple,
        coords_dadas=True,
        avisos=avisos,
    )


# ---------------------------------------------------------------------------
# Método 2: lados + diagonales (triangulación y Herón)
# ---------------------------------------------------------------------------
def _tercer_vertice(p_base, p_otro, d_base, d_otro):
    """Punto a distancia d_base de p_base y d_otro de p_otro, a la izquierda de p_base->p_otro."""
    L = distancia(p_base, p_otro)
    a = (d_base ** 2 - d_otro ** 2 + L ** 2) / (2 * L)
    h2 = d_base ** 2 - a ** 2
    h = math.sqrt(max(h2, 0.0))
    ux, uy = (p_otro[0] - p_base[0]) / L, (p_otro[1] - p_base[1]) / L
    px, py = p_base[0] + a * ux, p_base[1] + a * uy
    # izquierda = rotar +90°
    return (px - h * uy, py + h * ux)


def calcular_por_lados(lados, diagonales=None, nombres=None) -> Resultado:
    """
    lados:       [AB, BC, CD, ..., (último)-A]  (n valores)
    diagonales:  [AC, AD, ..., A(n-2)]          (n-3 valores, desde el vértice A)
    """
    lados = [float(x) for x in lados]
    n = len(lados)
    if n < 3:
        raise ErrorDatos("Se necesitan al menos 3 lados.")
    diagonales = [float(x) for x in (diagonales or [])]
    if len(diagonales) != n - 3:
        raise ErrorDatos(f"Para un polígono de {n} lados se necesitan {n - 3} diagonales "
                         "desde el primer vértice.")
    for i, d in enumerate(lados):
        if d <= 0:
            raise ErrorDatos(f"El lado {i + 1} debe ser mayor que cero.")
    for i, d in enumerate(diagonales):
        if d <= 0:
            raise ErrorDatos(f"La diagonal {i + 1} debe ser mayor que cero.")

    nombres = list(nombres) if nombres else nombres_vertices(n)
    nom_lados = nombres_lados(nombres)

    # Distancia desde el vértice A a cada vértice k (k = 1..n-1)
    # d_A[1] = lado AB, d_A[k] = diagonal A-k (2..n-2), d_A[n-1] = último lado (cierre)
    dA = {1: lados[0], n - 1: lados[-1]}
    for idx, k in enumerate(range(2, n - 1)):
        dA[k] = diagonales[idx]

    triangulos = []
    for k in range(1, n - 1):
        a, b, c = dA[k], lados[k], dA[k + 1]
        triangulos.append(heron(a, b, c, f"{nombres[0]}{nombres[k]}{nombres[k + 1]}"))

    # Reconstrucción de coordenadas (para el gráfico) en sistema local
    coords = [(0.0, 0.0), (0.0, lados[0])]  # A en el origen, B al Norte
    for k in range(2, n):
        # Se coloca a la derecha para un recorrido horario (convención topográfica)
        p = _tercer_vertice(coords[k - 1], coords[0], lados[k - 1], dA[k])
        coords.append(p)
    area_total = sum(t.area for t in triangulos)

    avisos = []
    simple = es_poligono_simple(coords)
    if not simple:
        avisos.append("Con las distancias ingresadas la figura reconstruida tiene lados que se "
                      "cruzan; revise los datos.")
    convexo = es_convexo(coords)
    if not convexo and simple:
        avisos.append("La figura es no convexa: el método supone que todas las diagonales "
                      "desde el vértice A quedan dentro del terreno.")

    return Resultado(
        metodo="triangulacion",
        nombres=nombres,
        coords=coords,
        lados=nom_lados,
        distancias=lados,
        area=area_total,
        perimetro=sum(lados),
        angulos=angulos_internos(coords) if simple else [],
        azimuts=[azimut(coords[i], coords[(i + 1) % n]) for i in range(n)],
        triangulos=triangulos,
        diagonales=[(f"{nombres[0]}-{nombres[k]}", dA[k]) for k in range(2, n - 1)],
        area_heron=area_total,
        convexo=convexo,
        simple=simple,
        coords_dadas=False,
        avisos=avisos,
    )


# ---------------------------------------------------------------------------
# Método 3: lados + ángulos internos (poligonal cerrada)
# ---------------------------------------------------------------------------
def calcular_por_angulos(lados, angulos, azimut_inicial=0.0, origen=(0.0, 0.0),
                         nombres=None, sentido="horario") -> Resultado:
    """
    lados:    distancias [AB, BC, ..., (último)-A]
    angulos:  ángulos internos medidos en cada vértice [A, B, C, ...] (grados decimales)
    azimut_inicial: azimut del lado AB (grados)
    sentido:  "horario" o "antihorario" (sentido en que se recorre el polígono)
    """
    lados = [float(x) for x in lados]
    angulos_med = [float(x) for x in angulos]
    n = len(lados)
    if n < 3:
        raise ErrorDatos("Se necesitan al menos 3 lados.")
    if len(angulos_med) != n:
        raise ErrorDatos("Debe ingresar un ángulo interno por cada vértice.")
    for i, d in enumerate(lados):
        if d <= 0:
            raise ErrorDatos(f"El lado {i + 1} debe ser mayor que cero.")
    for i, a in enumerate(angulos_med):
        if not 0 < a < 360:
            raise ErrorDatos(f"El ángulo del vértice {i + 1} debe estar entre 0° y 360°.")

    nombres = list(nombres) if nombres else nombres_vertices(n)
    suma_teorica = (n - 2) * 180.0
    error_ang = sum(angulos_med) - suma_teorica
    tolerancia_burda = 1.0 * n  # 1° por vértice: por encima es claramente un error de datos
    if abs(error_ang) > tolerancia_burda:
        raise ErrorDatos(
            f"La suma de ángulos internos es {sum(angulos_med):.4f}° y debería ser "
            f"{suma_teorica:.0f}° (error de {error_ang:+.4f}°). Revise los ángulos."
        )
    corr = -error_ang / n
    angulos_comp = [a + corr for a in angulos_med]

    # Azimuts: recorrido horario  -> Az_sig = Az_ant + 180 - ángulo_interno
    #          recorrido antihorario -> Az_sig = Az_ant + 180 + ángulo_interno
    azs = [azimut_inicial % 360.0]
    for i in range(1, n):
        ang = angulos_comp[i]
        if sentido == "horario":
            az = azs[-1] + 180.0 - ang
        else:
            az = azs[-1] + 180.0 + ang
        azs.append(az % 360.0)

    proy = [(d * math.sin(math.radians(az)), d * math.cos(math.radians(az)))
            for d, az in zip(lados, azs)]
    err_e = sum(p[0] for p in proy)
    err_n = sum(p[1] for p in proy)
    perimetro = sum(lados)
    error_lineal = math.hypot(err_e, err_n)
    precision = perimetro / error_lineal if error_lineal > 1e-12 else float("inf")

    # Coordenadas sin compensar y compensadas (Bowditch)
    sin_comp = [tuple(origen)]
    comp = [tuple(origen)]
    for i in range(n - 1):
        de, dn = proy[i]
        sin_comp.append((sin_comp[-1][0] + de, sin_comp[-1][1] + dn))
        ce = -err_e * lados[i] / perimetro
        cn = -err_n * lados[i] / perimetro
        comp.append((comp[-1][0] + de + ce, comp[-1][1] + dn + cn))

    area_signo = area_gauss_con_signo(comp)
    if abs(area_signo) < 1e-9:
        raise ErrorDatos("Los datos producen una figura de área cero.")

    avisos = []
    simple = es_poligono_simple(comp)
    if not simple:
        avisos.append("La poligonal calculada tiene lados que se cruzan. Verifique el sentido "
                      "de recorrido y los ángulos ingresados.")
    if precision < 1000:
        avisos.append(f"Precisión relativa 1/{precision:,.0f}: el cierre es deficiente "
                      "(se recomienda al menos 1/5000 para levantamientos con cinta).")

    triangulos = _triangulacion_desde_v1(comp, nombres)
    orient = 1 if area_signo > 0 else -1
    for t in triangulos:
        t.signo *= orient

    return Resultado(
        metodo="angulos",
        nombres=nombres,
        coords=comp,
        lados=nombres_lados(nombres),
        distancias=lados,
        area=abs(area_signo),
        perimetro=perimetro,
        angulos=angulos_comp,
        azimuts=azs,
        triangulos=triangulos,
        productos=productos_gauss(comp),
        area_heron=abs(sum(t.signo * t.area for t in triangulos)),
        convexo=es_convexo(comp),
        simple=simple,
        coords_dadas=False,
        avisos=avisos,
        error_angular=error_ang,
        angulos_medidos=angulos_med,
        error_cierre_lineal=error_lineal,
        precision=precision,
        coords_sin_compensar=sin_comp,
    )
