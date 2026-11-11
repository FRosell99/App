# Cálculo de Área de Polígonos — Matemática Aplicada (SENCICO)

Aplicación para el curso de **Matemática Aplicada**, Ciclo I de Topografía y Geodesia.
Calcula el área de un terreno (triángulo o polígono de *n* lados) y genera un **reporte PDF**
con el gráfico, los cuadros de datos y el desarrollo del cálculo.

## Cómo ejecutar

```bash
cd App
pip install -r requirements.txt
streamlit run app_poligono.py
```

Se abre en el navegador (http://localhost:8501).

## Formas de ingresar los datos

| Datos disponibles | Método de cálculo | Cuadro en el PDF |
|---|---|---|
| **Coordenadas** (Este, Norte) de los *n* vértices | Fórmula de Gauss (determinantes), verificada con triangulación + Herón | Cuadro de coordenadas |
| **Lados y distancias** (+ *n*−3 diagonales desde A si *n* > 3) | Triangulación + **fórmula de Herón** | Cuadro de lados y distancias |
| **Lados, distancias y ángulos internos** | Compensación angular, azimuts, coordenadas (Bowditch) + Gauss | Cuadro de lados/ángulos y de coordenadas calculadas |

### Fórmulas

- **Herón:** `s = (a + b + c) / 2`, `A = √[s(s − a)(s − b)(s − c)]`
- **Gauss:** `A = ½ · |Σ(Xᵢ·Yᵢ₊₁ − Xᵢ₊₁·Yᵢ)|`
- **Suma de ángulos internos:** `(n − 2) · 180°`

> Con solo los lados, un polígono de más de 3 lados no queda definido (puede “deformarse”),
> por eso se piden las diagonales desde el vértice A para dividirlo en triángulos.

## Reporte PDF

Incluye: datos del terreno, gráfico del polígono (vértices, distancias, Norte),
cuadro de coordenadas y/o cuadro de lados y distancias, tabla de productos de Gauss,
tabla de triángulos con Herón y el **área en m² y hectáreas** junto con el perímetro.

## Archivos

- `app_poligono.py` — interfaz (Streamlit)
- `poligono_calculos.py` — fórmulas y validaciones
- `poligono_reporte.py` — gráfico (matplotlib) y PDF (reportlab)
- `tests/` — pruebas (`python -m pytest tests`)
