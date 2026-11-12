#!/usr/bin/env python3
"""Pruebas de los scripts del kit contra valores conocidos. Uso: python tools/probar_scripts.py"""
import json
import math
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(RAIZ, "kit", "skills")


def ej(skill, nombre):
    return os.path.join(SK, skill, "ejemplos", nombre)
fallas = []


def ok(nombre, cond, detalle=""):
    print(("  bien  " if cond else "  FALLA ") + nombre + (f"  [{detalle}]" if detalle else ""))
    if not cond:
        fallas.append(nombre)


def correr(script, *args):
    # Igual que un Windows sin configurar: sin PYTHONIOENCODING ni PYTHONUTF8, con la salida capturada
    entorno = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    r = subprocess.run([sys.executable, os.path.join(SK, script), *args], capture_output=True, text=True, encoding="utf-8", env=entorno)
    return r.returncode, r.stdout, r.stderr


def cerca(a, b, rel):
    return abs(a - b) <= rel * abs(b)


for carpeta in ("ensayo-bombeo", "tendencia-niveles", "mapa-piezometrico", "calibracion-modelo", "unidades-hidro"):
    sys.path.insert(0, os.path.join(SK, carpeta, "scripts"))
from ensayo_bombeo import w_theis  # noqa: E402
from tendencia import mann_kendall, sen  # noqa: E402
from piezometria import plano, interpolar, curvas, rumbo  # noqa: E402
from calibracion import estadisticos  # noqa: E402
from unidades import convertir  # noqa: E402

BOMBEO = "ensayo-bombeo/scripts/ensayo_bombeo.py"
IONICO = "balance-ionico/scripts/balance_ionico.py"
TENDENCIA = "tendencia-niveles/scripts/tendencia.py"
PIEZO = "mapa-piezometrico/scripts/piezometria.py"
CALIB = "calibracion-modelo/scripts/calibracion.py"

print("ensayo-bombeo")
tabla = {1e-4: 8.6332, 1e-3: 6.3315, 1e-2: 4.0379, 0.1: 1.8229, 1.0: 0.2194, 2.0: 0.04890, 5.0: 0.0011483}
for u, w in tabla.items():
    ok(f"W({u:g}) = {w}", cerca(w_theis(u), w, 2e-4), f"{w_theis(u):.5f}")
try:
    from scipy.special import exp1
    peor = max(abs(w_theis(u) - exp1(u)) / exp1(u) for u in [10 ** (k / 10) for k in range(-80, 15)])
    ok("W(u) coincide con scipy.special.exp1", peor < 1e-9, f"error relativo maximo {peor:.1e}")
except ImportError:
    print("  (scipy no esta instalado: se omite la comparacion)")
c, out, err = correr(BOMBEO, ej("ensayo-bombeo", "ensayo-bombeo.csv"), "--q", "12", "--r", "35", "--b", "40", "--json")
ok("corre sin error", c == 0, err.strip()[:200])
d = json.loads(out)
por = {x["metodo"]: x for x in d["resultados"]}
ok("Theis recupera T = 450 m2/d", cerca(por["Theis"]["T_m2_d"], 450, 0.02), f"{por['Theis']['T_m2_d']:.1f}")
ok("Theis recupera S = 2e-4", cerca(por["Theis"]["S"], 2e-4, 0.05), f"{por['Theis']['S']:.3e}")
ok("Cooper-Jacob recupera T = 450 m2/d", cerca(por["Cooper-Jacob"]["T_m2_d"], 450, 0.03), f"{por['Cooper-Jacob']['T_m2_d']:.1f}")
ok("Cooper-Jacob recupera S = 2e-4", cerca(por["Cooper-Jacob"]["S"], 2e-4, 0.08), f"{por['Cooper-Jacob']['S']:.3e}")
ok("K = T/b", cerca(por["Theis"]["K_m_d"], por["Theis"]["T_m2_d"] / 40, 1e-9))
ok("u maximo de Cooper-Jacob bajo 0,05", por["Cooper-Jacob"]["u_maximo"] < 0.05, f"{por['Cooper-Jacob']['u_maximo']:.3f}")
ok("la derivada reconoce flujo radial y da T cerca de 450 m2/d", "flujo radial" in d["diagnostico"]["lectura"] and cerca(d["diagnostico"]["T_derivada_m2_d"], 450, 0.10), f"{d['diagnostico']['T_derivada_m2_d']:.0f}")
c, out, err = correr(BOMBEO, ej("ensayo-bombeo", "recuperacion.csv"), "--q", "12", "--recuperacion", "--tp", "1440", "--json")
d = json.loads(out)
ok("Recuperacion recupera T = 450 m2/d", c == 0 and cerca(d["resultados"][0]["T_m2_d"], 450, 0.05), f"{d['resultados'][0]['T_m2_d']:.1f}")
c, out, err = correr(BOMBEO, ej("ensayo-bombeo", "recuperacion.csv"), "--q", "12", "--recuperacion", "--tp", "1440", "--grafico", "x.png")
ok("recuperacion en Markdown informa el tramo y avisa que no hay grafico", c == 0 and "tramo usado t/t'" in out and "solo está disponible" in err, err.strip()[:80])
c, out, err = correr(BOMBEO, ej("ensayo-bombeo", "ensayo-bombeo.csv"), "--q", "12", "--r", "35", "--b", "40")
ok("Markdown con simbolos (t0, m2) sin configurar la consola", c == 0 and "t₀" in out and "## Diagnóstico" in out and "m²/d" in out, err.strip()[:120])
with tempfile.TemporaryDirectory() as tmp:
    ruta = os.path.join(tmp, "punto_y_coma.csv")
    with open(ej("ensayo-bombeo", "ensayo-bombeo.csv"), encoding="utf-8") as f:
        txt = f.read().replace(",", ";").replace(".", ",")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(txt)
    c, out, err = correr(BOMBEO, ruta, "--q", "12", "--r", "35", "--json")
    ok("lee CSV con punto y coma y coma decimal", c == 0 and cerca(json.loads(out)["resultados"][1]["T_m2_d"], 450, 0.02))
    png = os.path.join(tmp, "g.png")
    c, out, err = correr(BOMBEO, ej("ensayo-bombeo", "ensayo-bombeo.csv"), "--q", "12", "--r", "35", "--grafico", png)
    ok("salida en Markdown y grafico", c == 0 and "| Theis |" in out and (os.path.exists(png) or "matplotlib" in err))

print("balance-ionico")
with tempfile.TemporaryDirectory() as tmp:
    svg = os.path.join(tmp, "piper.svg")
    c, out, err = correr(IONICO, ej("balance-ionico", "hidroquimica.csv"), "--piper", svg, "--json")
    ok("corre sin error", c == 0, err.strip()[:200])
    m = {x["muestra"]: x for x in json.loads(out)["muestras"]}
    ok("PZ-01 suma 5,10 meq/L de cationes", cerca(m["PZ-01"]["suma_cationes_meq"], 5.10, 0.01), f"{m['PZ-01']['suma_cationes_meq']:.3f}")
    ok("PZ-01 error cerca de +0,5 %", abs(m["PZ-01"]["error_pct"] - 0.49) < 0.2, f"{m['PZ-01']['error_pct']:.2f}")
    ok("PZ-01 aceptada y bicarbonatada calcica", m["PZ-01"]["estado"] == "aceptada" and m["PZ-01"]["tipo"] == "Bicarbonatada cálcica", m["PZ-01"]["tipo"])
    ok("PZ-02 sulfatada calcica", m["PZ-02"]["tipo"] == "Sulfatada cálcica", m["PZ-02"]["tipo"])
    ok("PZ-03 clorurada sodica", m["PZ-03"]["tipo"] == "Clorurada sódica", m["PZ-03"]["tipo"])
    ok("PZ-05 rechazada con error cerca de +11,4 %", m["PZ-05"]["estado"] == "rechazada" and abs(m["PZ-05"]["error_pct"] - 11.39) < 0.3, f"{m['PZ-05']['error_pct']:.2f}")
    ok("SDT medido/calculado = 1,06", cerca(m["PZ-02"]["razon_sdt"], 1.06, 0.01), f"{m['PZ-02']['razon_sdt']:.3f}")
    ok("Piper escrito con 6 muestras", os.path.exists(svg) and open(svg, encoding="utf-8").read().count("<circle") >= 18)
    ruta = os.path.join(tmp, "limite.csv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("muestra;Ca;Mg;Na;K;HCO3;Cl;SO4;NO3\nA;60,1;12,2;23,0;3,9;219,7;21,3;38,4;<0,5\n")
    c, out, err = correr(IONICO, ruta, "--json")
    x = json.loads(out)["muestras"][0]
    ok("valor bajo el limite y coma decimal", c == 0 and x["bajo_limite"] == ["NO3"] and x["estado"] == "aceptada", str(x["bajo_limite"]))
    c, out, err = correr(IONICO, ej("balance-ionico", "hidroquimica.csv"))
    ok("salida en Markdown", c == 0 and "| PZ-05 |" in out and "rechazada" in out)

print("tendencia-niveles")
s, var, z, p = mann_kendall(list(range(1, 11)))
ok("Mann-Kendall de 1..10: S = 45, Var = 125, Z = 3,935", s == 45 and var == 125 and cerca(z, 3.9355, 1e-3), f"S={s} var={var} z={z:.4f} p={p:.2e}")
s, var, z, p = mann_kendall([1, 2, 2, 3, 3, 3, 4])
ok("correccion por empates", cerca(var, (7 * 6 * 19 - (2 * 1 * 9 + 3 * 2 * 11)) / 18, 1e-12), f"var={var:.3f}")
ok("Sen de una recta exacta", cerca(sen([0, 1, 2, 3], [5, 7, 9, 11]), 2.0, 1e-12))
c, out, err = correr(TENDENCIA, ej("tendencia-niveles", "niveles-monitoreo.csv"), "--json")
ok("corre sin error", c == 0, err.strip()[:200])
pt = {x["punto"]: x for x in json.loads(out)["puntos"]}
ok("PM-01 decreciente a -0,42 m/ano", pt["PM-01"]["tendencia"] == "decreciente" and cerca(pt["PM-01"]["sen_por_ano"], -0.42, 0.08), f"{pt['PM-01']['sen_por_ano']:.3f}")
ok("PM-02 sin tendencia", pt["PM-02"]["tendencia"] == "sin tendencia", f"p={pt['PM-02']['p']:.2f}")
ok("PM-03 creciente a +0,18 m/ano", pt["PM-03"]["tendencia"] == "creciente" and cerca(pt["PM-03"]["sen_por_ano"], 0.18, 0.15), f"{pt['PM-03']['sen_por_ano']:.3f}")
ok("PM-03 detecta la lectura anomala de julio de 2023", [a["fecha"] for a in pt["PM-03"]["anomalos"]] == ["2023-07-15"], str(pt["PM-03"]["anomalos"]))
c, out, err = correr(TENDENCIA, ej("tendencia-niveles", "niveles-monitoreo.csv"), "--unidad", "m")
ok("salida en Markdown", c == 0 and "| PM-01 | 60 |" in out)

print("mapa-piezometrico")
pts = [("A", 0, 0, 100.0), ("B", 1000, 0, 100.0), ("C", 0, 1000, 110.0), ("D", 1000, 1000, 110.0)]
pl = plano(pts)
ok("plano: gradiente 0,01 y flujo hacia el sur", cerca(pl["gradiente"], 0.01, 1e-9) and abs(pl["azimut_flujo"] - 180) < 1e-6 and rumbo(pl["azimut_flujo"]) == "S", f"{pl['gradiente']:.4f} {pl['azimut_flujo']:.1f}")
pl2 = plano([("A", 0, 0, 105.0), ("B", 1000, 0, 100.0), ("C", 0, 1000, 105.0)])
ok("tres puntos: flujo hacia el este", abs(pl2["azimut_flujo"] - 90) < 1e-6 and cerca(pl2["gradiente"], 0.005, 1e-9), f"{pl2['azimut_flujo']:.1f}")
g = {"x0": 0.0, "y0": 0.0, "celda": 10.0, "nx": 11, "ny": 11, "z": [[100 + j for i in range(11)] for j in range(11)]}
cv = curvas(g, [105.0])
ok("curva de 105 es una sola linea recta en y = 50", len(cv[105.0]) == 1 and all(abs(q[1] - 50) < 1e-4 for q in cv[105.0][0]) and len(cv[105.0][0]) == 11, f"{len(cv[105.0])} lineas, {len(cv[105.0][0])} vertices")
g2 = {"x0": 0.0, "y0": 0.0, "celda": 1.0, "nx": 21, "ny": 21, "z": [[math.hypot(i - 10, j - 10) for i in range(21)] for j in range(21)]}
cv2 = curvas(g2, [5.0])
li = cv2[5.0][0]
ok("curva cerrada alrededor de un cono", len(cv2[5.0]) == 1 and math.hypot(li[0][0] - li[-1][0], li[0][1] - li[-1][1]) < 1e-6 and all(abs(math.hypot(q[0] - 10, q[1] - 10) - 5) < 0.15 for q in li), f"{len(cv2[5.0])} lineas, {len(li)} vertices")
with tempfile.TemporaryDirectory() as tmp:
    c, out, err = correr(PIEZO, ej("mapa-piezometrico", "piezometria.csv"), "--epsg", "32719", "--salida", tmp, "--json")
    ok("corre sin error", c == 0, err.strip()[:200])
    r = json.loads(out)
    ok("flujo hacia el suroeste", 200 < r["azimut_flujo_grados"] < 235, f"{r['azimut_flujo_grados']:.0f} grados {r['rumbo_flujo']}")
    ok("gradiente cerca de 0,004", 0.003 < r["gradiente_regional"] < 0.005, f"{r['gradiente_regional']:.5f}")
    with open(os.path.join(tmp, "curvas.geojson"), encoding="utf-8") as f:
        gj = json.load(f)
    ok("GeoJSON valido con curvas y sistema de coordenadas", len(gj["features"]) >= 4 and "32719" in gj["crs"]["properties"]["name"], f"{len(gj['features'])} curvas")
    with open(os.path.join(tmp, "grilla.asc")) as f:
        asc = f.read().split("\n")
    ok("grilla ASCII con encabezado", asc[0].startswith("ncols") and len(asc[6].split()) == int(asc[0].split()[1]))
    with open(os.path.join(tmp, "vista.svg"), encoding="utf-8") as f:
        ok("vista SVG escrita", f.read().count("<path") >= 4)
    c, out, err = correr(PIEZO, ej("mapa-piezometrico", "piezometria.csv"), "--salida", tmp)
    ok("salida en Markdown", c == 0 and "Dirección de flujo" in out and "(SO)" in out, err.strip()[:120])
    zz = interpolar([("A", 0, 0, 10.0), ("B", 100, 0, 20.0), ("C", 0, 100, 30.0)], celda=50, margen=0)["z"]
    ok("la interpolacion respeta los valores medidos", zz[0][0] == 10.0 and zz[0][2] == 20.0 and zz[2][0] == 30.0)

print("calibracion-modelo")
e = estadisticos([(10, 11), (20, 19), (30, 32), (40, 40)])
ok("error medio 0,5; MAE 1,0; RMSE 1,2247; normalizado 4,08 %", cerca(e["error_medio"], 0.5, 1e-12) and cerca(e["error_medio_absoluto"], 1.0, 1e-12) and cerca(e["rmse"], math.sqrt(1.5), 1e-12) and cerca(e["rmse_normalizado_pct"], 100 * math.sqrt(1.5) / 30, 1e-12), f"{e['rmse']:.4f} {e['rmse_normalizado_pct']:.2f}")
c, out, err = correr(CALIB, ej("calibracion-modelo", "calibracion.csv"), "--json")
d = json.loads(out)
ok("corre con el ejemplo y separa por capa", c == 0 and set(d["por_grupo"]) == {"capa 1", "capa 2"} and d["total"]["n"] == 18, err.strip()[:200])
c, out, err = correr(CALIB, ej("calibracion-modelo", "calibracion.csv"))
ok("salida en Markdown", c == 0 and "| Total | 18 |" in out)

print("unidades-hidro")
casos = [(1e-5, "m/s", "m/d", 0.864), (12, "L/s", "m3/d", 1036.8), (450, "m2/d", "m2/s", 450 / 86400), (1, "cm/s", "m/día", 864.0),
         (100, "l/s", "m³/h", 360.0), (1, "hm3/año", "L/s", 1e6 / (365.25 * 86400) * 1000), (1, "ft/d", "m/d", 0.3048),
         (1, "gpm", "L/s", 0.0630902), (1, "gpd/ft", "m2/d", 0.0124193), (1, "gpd/ft2", "m/d", 0.0407458), (2.5, "km2", "ha", 250.0)]
for v, a, b, esperado in casos:
    r = convertir(v, a, b)[0]
    ok(f"{v:g} {a} = {esperado:.6g} {b}", cerca(r, esperado, 1e-5), f"{r:.6g}")
c, out, err = correr("unidades-hidro/scripts/unidades.py", "1", "m/año", "mm/d")
ok("desde la consola: 1 m/año = 2,73785 mm/d", c == 0 and "2.73785 mm/d" in out and "conductividad hidráulica" in out, (out + err).strip()[:100])
c, out, err = correr("unidades-hidro/scripts/unidades.py", "--lista")
ok("lista de unidades con acentos", c == 0 and "área" in out)
try:
    convertir(1, "m/s", "L/s")
    ok("rechaza magnitudes distintas", False)
except ValueError:
    ok("rechaza magnitudes distintas", True)

print()
if fallas:
    print(f"{len(fallas)} pruebas fallaron:")
    for f in fallas:
        print("  - " + f)
    sys.exit(1)
print("Todas las pruebas pasaron.")
