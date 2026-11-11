#!/usr/bin/env python3
"""Genera los datos de ejemplo del kit (ficticios y reproducibles)."""
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kit", "skills", "ensayo-bombeo", "scripts"))
from ensayo_bombeo import w_theis  # noqa: E402

SK = os.path.join(RAIZ, "kit", "skills")


def ruido(i, amp):
    """Ruido determinista, sin azar: igual en cada ejecución."""
    return amp * math.sin(12.9898 * (i + 1)) * math.cos(4.1414 * (i + 3))


def escribir(skill, nombre, lineas):
    carpeta = os.path.join(SK, skill, "ejemplos")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, nombre), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")


# 1. Ensayo de bombeo: T = 450 m2/d, S = 2e-4, Q = 12 L/s, r = 35 m, 24 h
T, S, Q, R = 450.0, 2e-4, 12 * 86.4, 35.0
tiempos = [1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 75, 90, 120, 150, 180, 240,
           300, 360, 480, 600, 720, 900, 1080, 1260, 1440]
filas = ["t_min,s_m"]
for i, t in enumerate(tiempos):
    s = Q / (4 * math.pi * T) * w_theis(R ** 2 * S / (4 * T * t / 1440)) + ruido(i, 0.004)
    filas.append(f"{t:g},{s:.3f}")
escribir("ensayo-bombeo", "ensayo-bombeo.csv", filas)

# 2. Recuperación del mismo ensayo (descenso residual tras 1440 min de bombeo)
tp = 1440.0
filas = ["t_min,s_m"]
for i, dtp in enumerate([1, 2, 3, 5, 7, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720]):
    t = tp + dtp
    s = Q / (4 * math.pi * T) * (w_theis(R ** 2 * S / (4 * T * t / 1440)) - w_theis(R ** 2 * S / (4 * T * dtp / 1440)))
    filas.append(f"{t:g},{s + ruido(i, 0.003):.3f}")
escribir("ensayo-bombeo", "recuperacion.csv", filas)

# 3. Hidroquímica (definida en meq/L y convertida a mg/L)
PE = {"Ca": 20.039, "Mg": 12.1525, "Na": 22.9898, "K": 39.0983, "HCO3": 61.0168, "CO3": 30.0044,
      "Cl": 35.453, "SO4": 48.0313, "NO3": 62.0049}
muestras = [
    ("PZ-01", dict(Ca=3.0, Mg=1.0, Na=1.0, K=0.10, HCO3=3.6, CO3=0, Cl=0.6, SO4=0.8, NO3=0.05), 7.6),
    ("PZ-02", dict(Ca=9.0, Mg=3.0, Na=4.0, K=0.20, HCO3=2.5, CO3=0, Cl=3.0, SO4=10.5, NO3=0.10), 7.2),
    ("PZ-03", dict(Ca=6.0, Mg=5.0, Na=60.0, K=2.0, HCO3=3.0, CO3=0, Cl=58.0, SO4=11.0, NO3=0.0), 7.9),
    ("PZ-04", dict(Ca=4.0, Mg=2.5, Na=3.5, K=0.15, HCO3=4.0, CO3=0, Cl=3.0, SO4=3.0, NO3=0.10), 7.4),
    ("PZ-05", dict(Ca=5.0, Mg=2.0, Na=6.0, K=0.20, HCO3=3.0, CO3=0, Cl=4.0, SO4=3.5, NO3=0.0), 7.1),
    ("VT-01", dict(Ca=1.2, Mg=0.4, Na=0.5, K=0.05, HCO3=1.6, CO3=0, Cl=0.2, SO4=0.3, NO3=0.02), 7.8),
]
filas = ["muestra,pH,CE,SDT,Ca,Mg,Na,K,HCO3,CO3,Cl,SO4,NO3"]
for nombre, meq, ph in muestras:
    mg = {k: v * PE[k] for k, v in meq.items()}
    cationes = sum(meq[k] for k in ("Ca", "Mg", "Na", "K"))
    sdt = (sum(v for k, v in mg.items() if k != "HCO3") + 0.4917 * mg["HCO3"]) * 1.06
    filas.append(f"{nombre},{ph},{cationes * 98:.0f},{sdt:.0f}," + ",".join(f"{mg[k]:.1f}" for k in
                 ("Ca", "Mg", "Na", "K", "HCO3", "CO3", "Cl", "SO4", "NO3")))
escribir("balance-ionico", "hidroquimica.csv", filas)

# 4. Niveles de monitoreo: 5 años mensuales en 3 pozos
filas = ["fecha,punto,valor"]
k = 0
for a in range(2021, 2026):
    for m in range(1, 13):
        mes = (a - 2021) * 12 + (m - 1)
        est = 0.35 * math.sin(2 * math.pi * (m - 3) / 12)
        p1 = 512.40 - 0.42 * mes / 12 + est + ruido(k, 0.06)          # desciende 0,42 m/año
        p2 = 498.10 + 0.6 * est + ruido(k + 50, 0.08)                 # estable
        p3 = 505.75 + 0.18 * mes / 12 + 0.5 * est + ruido(k + 99, 0.05)  # asciende 0,18 m/año
        if (a, m) == (2023, 7):
            p3 += 3.2  # lectura anómala a propósito
        for nombre, v in (("PM-01", p1), ("PM-02", p2), ("PM-03", p3)):
            filas.append(f"{a}-{m:02d}-15,{nombre},{v:.2f}")
        k += 1
escribir("tendencia-niveles", "niveles-monitoreo.csv", filas)

# 5. Piezometría: 14 pozos sobre una superficie que baja hacia el suroeste, con leve curvatura
pozos = [(500350, 7400420), (501200, 7405300), (502480, 7401150), (503900, 7404600), (505100, 7400800),
         (505650, 7403250), (500900, 7402700), (502100, 7403900), (503300, 7402300), (504400, 7401700),
         (501700, 7400300), (504900, 7405500), (502900, 7405200), (500500, 7404400)]
filas = ["punto,x,y,nivel"]
for i, (x, y) in enumerate(pozos):
    dx, dy = (x - 500000) / 1000.0, (y - 7400000) / 1000.0
    h = 480.0 + 2.2 * dx + 3.1 * dy + 0.12 * dx * dy + ruido(i, 0.15)
    filas.append(f"P-{i + 1:02d},{x},{y},{h:.2f}")
escribir("mapa-piezometrico", "piezometria.csv", filas)

# 6. Calibración: observado contra simulado en dos capas
filas = ["punto,grupo,observado,simulado"]
for i in range(18):
    obs = 470.0 + 2.6 * i + ruido(i, 1.5)
    capa = "capa 1" if i % 3 else "capa 2"
    sesgo = 0.9 if capa == "capa 2" else -0.2
    sim = obs + sesgo + ruido(i + 20, 1.6)
    filas.append(f"OB-{i + 1:02d},{capa},{obs:.2f},{sim:.2f}")
escribir("calibracion-modelo", "calibracion.csv", filas)

print("Ejemplos generados en la carpeta ejemplos de cada skill")
