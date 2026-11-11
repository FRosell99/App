import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import poligono_calculos as pc  # noqa: E402


def test_heron_triangulo_3_4_5():
    t = pc.heron(3, 4, 5)
    assert t.s == 6
    assert t.area == pytest.approx(6.0)


def test_heron_desigualdad_triangular():
    with pytest.raises(pc.ErrorDatos):
        pc.heron(1, 2, 10)


def test_coordenadas_cuadrado_ambos_sentidos():
    cuadrado = [(0, 0), (0, 10), (10, 10), (10, 0)]
    for coords in (cuadrado, cuadrado[::-1]):
        r = pc.calcular_por_coordenadas(coords)
        assert r.area == pytest.approx(100)
        assert r.area_heron == pytest.approx(100)
        assert r.perimetro == pytest.approx(40)
        assert r.angulos == pytest.approx([90, 90, 90, 90])


def test_coordenadas_no_convexo_heron_con_signo():
    # Forma de "L": área 3
    coords = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]
    r = pc.calcular_por_coordenadas(coords)
    assert r.area == pytest.approx(3)
    assert r.area_heron == pytest.approx(3)
    assert not r.convexo
    assert sum(r.angulos) == pytest.approx(720)


def test_coordenadas_cruzadas_avisa():
    r = pc.calcular_por_coordenadas([(0, 0), (10, 10), (10, 0), (0, 6)])
    assert not r.simple
    assert r.avisos


def test_lados_triangulo():
    r = pc.calcular_por_lados([3, 4, 5])
    assert r.area == pytest.approx(6)
    # la figura reconstruida reproduce las distancias
    n = 3
    for i in range(n):
        assert pc.distancia(r.coords[i], r.coords[(i + 1) % n]) == pytest.approx(r.distancias[i])


def test_lados_y_diagonales_pentagono_regular():
    n, R = 5, 20.0
    coords = [(R * math.cos(2 * math.pi * k / n), R * math.sin(2 * math.pi * k / n)) for k in range(n)]
    esperado = pc.calcular_por_coordenadas(coords)
    lados = esperado.distancias
    diags = [pc.distancia(coords[0], coords[k]) for k in range(2, n - 1)]
    r = pc.calcular_por_lados(lados, diags)
    assert r.area == pytest.approx(esperado.area)
    for i in range(n):
        assert pc.distancia(r.coords[i], r.coords[(i + 1) % n]) == pytest.approx(lados[i])
    assert pc.area_gauss_con_signo(r.coords) == pytest.approx(-esperado.area)  # horario


def test_lados_numero_diagonales_incorrecto():
    with pytest.raises(pc.ErrorDatos):
        pc.calcular_por_lados([10, 10, 10, 10], [])


def test_angulos_rectangulo_horario_y_antihorario():
    for sentido in ("horario", "antihorario"):
        r = pc.calcular_por_angulos([30, 50, 30, 50], [90, 90, 90, 90], 0.0, sentido=sentido)
        assert r.area == pytest.approx(1500)
        assert r.error_cierre_lineal == pytest.approx(0, abs=1e-9)
        assert r.simple


def test_angulos_compensacion():
    # Rectángulo con pequeño error angular y lineal
    r = pc.calcular_por_angulos([30.02, 50, 29.99, 50.01], [90.01, 89.99, 90.02, 90.0], 45)
    assert r.error_angular == pytest.approx(0.02)
    assert sum(r.angulos) == pytest.approx(360)
    # tras Bowditch la poligonal cierra
    assert r.area == pytest.approx(1500, rel=1e-3)


def test_gms():
    assert pc.grados_a_gms(pc.gms_a_grados(45, 30, 15)) == "45°30'15\""
