#!/usr/bin/env python3
"""Pruebas de los scripts del kit contra valores conocidos. Uso: python tools/probar_scripts.py"""
import json
import math
import os
import subprocess
import sys
import tempfile

for _consola in (sys.stdout, sys.stderr):
    try:
        _consola.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

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

print("balance-acido-base")
sys.path.insert(0, os.path.join(SK, "balance-acido-base", "scripts"))
from aba import clasificar  # noqa: E402
k = clasificar(31.25 * 2.0, 20.0)
ok("S = 2 %: PA 62,5; PNN -42,5; razon 0,32; generador", cerca(k["PNN"], -42.5, 1e-12) and cerca(k["razon"], 0.32, 1e-12) and k["clase"] == "generador", f"{k['PNN']} {k['razon']}")
k = clasificar(10.0, 45.0)
ok("PA 10, PN 45: no generador por ambos criterios", k["clase"] == "no generador" and k["por_razon"] == k["por_pnn"])
k = clasificar(45.3125, 30.0)
ok("criterios que no coinciden dan incierto", k["por_razon"] == "generador" and k["por_pnn"] == "incierto" and k["clase"] == "incierto")
k = clasificar(0.0, 30.0)
ok("sin azufre no divide por cero", k["razon"] == float("inf") and k["clase"] == "no generador")
c, out, err = correr("balance-acido-base/scripts/aba.py", ej("balance-acido-base", "ensayos-estaticos.csv"), "--json")
ok("corre sin error", c == 0, err.strip()[:200])
d = json.loads(out)
m = {x["muestra"]: x for x in d["muestras"]}
ok("resumen del ejemplo: 4 generadoras, 4 inciertas, 4 no generadoras", d["resumen"] == {"generador": 4, "incierto": 4, "no generador": 4}, str(d["resumen"]))
ok("MR-07: PA 68,75 y PNN -50,75", cerca(m["MR-07"]["PA"], 68.75, 1e-9) and cerca(m["MR-07"]["PNN"], -50.75, 1e-9))
ok("MR-12 usa azufre total y lo avisa", cerca(m["MR-12"]["PA"], 40.625, 1e-9) and any("azufre total" in a for a in m["MR-12"]["avisos"]))
ok("MR-09 avisa acidez actual por pH en pasta", any("ya presenta acidez" in a for a in m["MR-09"]["avisos"]))
ok("lista las muestras que piden ensayo cinetico", d["requieren_cinetico"] == ["MR-04", "MR-05", "MR-06", "MR-12"], str(d["requieren_cinetico"]))
ok("resumen por grupo", d["por_grupo"]["brecha"]["generador"] == 3 and d["por_grupo"]["andesita"]["no generador"] == 3, str(d["por_grupo"]))
c, out, err = correr("balance-acido-base/scripts/aba.py", ej("balance-acido-base", "ensayos-estaticos.csv"))
ok("salida en Markdown", c == 0 and "| MR-07 |" in out and "kg CaCO₃/t" in out)

print("phreeqc-entrada")
with tempfile.TemporaryDirectory() as tmp:
    pqi = os.path.join(tmp, "aguas.pqi")
    c, out, err = correr("phreeqc-entrada/scripts/phreeqc_entrada.py", ej("phreeqc-entrada", "aguas.csv"), "--salida", pqi, "--json")
    ok("corre sin error", c == 0, err.strip()[:200])
    d = json.loads(out)
    with open(pqi, encoding="utf-8") as f:
        t = f.read()
    ok("seis bloques SOLUTION y seis END", t.count("\nSOLUTION ") == 6 and t.count("\nEND") == 6 and len(d["soluciones"]) == 6)
    ok("un SELECTED_OUTPUT antes de la primera solucion", t.count("SELECTED_OUTPUT 1") == 1 and t.index("SELECTED_OUTPUT") < t.index("\nSOLUTION "))
    ok("unidades, pH, temperatura y alcalinidad de PZ-01", "SOLUTION 1 PZ-01\n    units mg/l\n    pH 7.6\n    temp 16.5\n" in t and "    Alkalinity 219.7 as HCO3" in t)
    ok("sulfato, nitrato y silice con su formula", "    S(6) 38.4 as SO4" in t and "    N(5) 3.1 as NO3" in t and "    Si 28 as SiO2" in t)
    ok("pe supuesto queda marcado", t.count("pe 4    # supuesto") == 6 and "pe de 4" in d["supuestos"])
    ok("arsenico queda como comentario con phreeqc.dat", "# As 0.004    # no está en phreeqc.dat" in t and "\n    As " not in t and any("As" in a for a in d["avisos"]))
    ok("hierro bajo el limite no se incluye", "# Fe: bajo el límite de detección" in t)
    ok("fases segun los elementos presentes", "Goethite" in d["fases"] and "Gibbsite" not in d["fases"] and "Calcite" in d["fases"])
    ok("fuerza ionica aproximada de PZ-03 cerca de 0,08", 0.06 < d["soluciones"][2]["fuerza_ionica_aprox"] < 0.10, f"{d['soluciones'][2]['fuerza_ionica_aprox']:.3f}")
    c, out, err = correr("phreeqc-entrada/scripts/phreeqc_entrada.py", ej("phreeqc-entrada", "aguas.csv"), "--salida", pqi, "--base", "wateq4f.dat", "--balancear", "Cl", "--json")
    with open(pqi, encoding="utf-8") as f:
        t = f.read()
    ok("con wateq4f.dat el arsenico se incluye y el cloruro balancea", c == 0 and "\n    As 0.004\n" in t and "    Cl 21.3    charge" in t)
    ruta = os.path.join(tmp, "salmuera.csv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("muestra;pH;alcalinidad;Na;Cl;SO4;Li\nSM-1;7,1;350;95000;150000;18000;1200\n")
    c, out, err = correr("phreeqc-entrada/scripts/phreeqc_entrada.py", ruta, "--json")
    d = json.loads(out)
    with open(d["archivo"], encoding="utf-8") as f:
        t = f.read()
    ok("salmuera: alcalinidad como CaCO3 y aviso de usar pitzer.dat", c == 0 and "Alkalinity 350 as CaCO3" in t and any("pitzer.dat" in a for a in d["avisos"]), str(d["avisos"])[:120])

print("balance-aguas")
sys.path.insert(0, os.path.join(SK, "balance-aguas", "scripts"))
from balance_aguas import cerrar  # noqa: E402
r = cerrar([("entrada", 100.0), ("salida", 60.0), ("salida", 30.0), ("almacenamiento", 8.0)], 5.0)
ok("cierre 2, error 2 %, cierra", cerca(r["cierre"], 2.0, 1e-12) and cerca(r["error_pct"], 2.0, 1e-12) and r["estado"] == "cierra")
r = cerrar([("entrada", 100.0), ("salida", 120.0)], 5.0)
ok("error negativo sobre el doble de la tolerancia: no cierra", cerca(r["error_pct"], -100 * 20 / 120, 1e-12) and r["estado"] == "no cierra")
c, out, err = correr("balance-aguas/scripts/balance_aguas.py", ej("balance-aguas", "balance-relaves.csv"), "--json")
ok("corre sin error", c == 0, err.strip()[:200])
d = json.loads(out)
ok("enero cierra con +0,17 %", d["periodos"]["2025-01"]["estado"] == "cierra" and cerca(d["periodos"]["2025-01"]["error_pct"], 100 * 2000 / 1207000, 1e-9))
ok("febrero queda para revisar con +5,58 %", d["periodos"]["2025-02"]["estado"] == "revisar" and cerca(d["periodos"]["2025-02"]["error_pct"], 100 * 70000 / 1255000, 1e-9), f"{d['periodos']['2025-02']['error_pct']:.2f}")
ok("avisa que el error tiene el mismo signo en todos los periodos", any("mismo signo" in a for a in d["avisos"]))
ok("el agua con la pulpa pesa 97 % de las entradas", cerca(next(x for x in d["desglose"] if x["componente"] == "Agua con la pulpa")["porcentaje"], 100 * 3530000 / 3642000, 1e-9))
c, out, err = correr("balance-aguas/scripts/balance_aguas.py", ej("balance-aguas", "balance-relaves.csv"), "--unidad", "m3/mes")
ok("salida en Markdown", c == 0 and "| 2025-02 |" in out and "revisar" in out and "| **Suma** |" in out)

print("salares")
sys.path.insert(0, os.path.join(SK, "salares", "scripts"))
from salares import carga_equivalente, ajustar_evaporacion  # noqa: E402
ok("carga equivalente: 2280 + 1,2 x 20 = 2304", cerca(carga_equivalente(2300.0, 2280.0, 1200.0), 2304.0, 1e-12))
ok("densidad en g/cm3 da lo mismo", cerca(carga_equivalente(2300.0, 2280.0, 1.2), 2304.0, 1e-12))
ok("agua dulce no cambia", cerca(carga_equivalente(2303.0, 2295.0, 1000.0), 2303.0, 1e-12))
aj = ajustar_evaporacion([0, 0.5, 1.0, 2.0], [8.0 * math.exp(-1.5 * z) for z in (0, 0.5, 1.0, 2.0)])
ok("ajuste exacto: E0 = 8, k = 1,5, extincion al 1 % a 3,07 m", cerca(aj["E0_mm_d"], 8.0, 1e-9) and cerca(aj["k_por_m"], 1.5, 1e-9) and cerca(aj["profundidad_1pct_m"], math.log(100) / 1.5, 1e-9))
c, out, err = correr("salares/scripts/salares.py", "carga", ej("salares", "niveles-densidad.csv"), "--json")
d = json.loads(out)
p = {x["punto"]: x for x in d["puntos"]}
ok("avisa la densidad en g/cm3 y la diferencia de cota entre tramos captados", "g/cm3" in p["SB-06"]["aviso"] and cerca(d["dispersion_cota_filtro_m"], 35.0, 1e-9) and any("flotación" in x for x in d["avisos"]))
ok("SB-01 = 2304,70 y SB-06 (g/cm3) = 2309,29", c == 0 and cerca(p["SB-01"]["carga_equivalente"], 2304.7025, 1e-9) and cerca(p["SB-06"]["carga_equivalente"], 2260 + 1.22 * 40.4, 1e-9), f"{p['SB-06']['carga_equivalente']:.3f}")
c, out, err = correr("salares/scripts/salares.py", "evaporacion", ej("salares", "evaporacion.csv"), "--json")
d = json.loads(out)
ok("ajuste por tipo de superficie", list(d["por_superficie"]) == ["costra"] and cerca(d["por_superficie"]["costra"]["E0_mm_d"], d["ajuste"]["E0_mm_d"], 1e-12))
ok("evaporacion del ejemplo: E0 cerca de 6 y k cerca de 2,5", c == 0 and cerca(d["ajuste"]["E0_mm_d"], 6.0, 0.08) and cerca(d["ajuste"]["k_por_m"], 2.5, 0.08), f"{d['ajuste']['E0_mm_d']:.2f} {d['ajuste']['k_por_m']:.2f}")
c, out, err = correr("salares/scripts/salares.py", "carga", ej("salares", "niveles-densidad.csv"))
c2, out2, err2 = correr("salares/scripts/salares.py", "evaporacion", ej("salares", "evaporacion.csv"))
ok("salidas en Markdown", c == 0 and c2 == 0 and "| SB-01 |" in out and "E₀" in out2 and "## Por tipo de superficie" in out2 and "cota similar" in out)
with tempfile.TemporaryDirectory() as tmp:
    ruta = os.path.join(tmp, "dos.csv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("superficie;profundidad;evaporacion\n" + "".join(f"costra;{z};{str(4.0 * math.exp(-3.0 * z)).replace('.', ',')}\n" for z in (0.1, 0.4, 0.8))
                + "".join(f"suelo;{z};{str(7.0 * math.exp(-1.2 * z)).replace('.', ',')}\n" for z in (0.2, 0.6, 1.0, 1.5)) + "vega;0,3;5,0\n")
    c, out, err = correr("salares/scripts/salares.py", "evaporacion", ruta, "--json")
    d = json.loads(out)
    ok("dos superficies se ajustan por separado y una con un solo dato queda sin ajuste", c == 0 and cerca(d["por_superficie"]["costra"]["k_por_m"], 3.0, 1e-6) and cerca(d["por_superficie"]["suelo"]["E0_mm_d"], 7.0, 1e-6) and "nota" in d["por_superficie"]["vega"] and any("más de un tipo" in x for x in d["avisos"]))

print("umbrales-alerta")
sys.path.insert(0, os.path.join(SK, "umbrales-alerta", "scripts"))
import datetime  # noqa: E402
from umbrales import evaluar  # noqa: E402
ser = [(datetime.date(2025, m, 1), v) for m, v in enumerate([10.0, 9.0, 8.0, 7.4, 6.9], 1)]
e = evaluar(ser, 7.5, 7.0, "bajo", 1)
ok("nivel bajo el umbral de accion: accion, racha 1, margen -0,6", e["estado"] == "acción" and e["racha_accion"] == 1 and e["racha_alerta"] == 2 and cerca(e["margen_a_alerta"], -0.6, 1e-9) and e["primera_superacion"] == "2025-04-01")
e = evaluar(ser, 7.5, 7.0, "bajo", 3)
ok("con 3 consecutivas queda en observacion", e["estado"] == "en observación")
e = evaluar([(datetime.date(2025, 1, 1), 100.0), (datetime.date(2025, 2, 1), 260.0)], 250.0, 400.0, "sobre", 1)
ok("concentracion sobre la alerta y bajo la accion", e["estado"] == "alerta" and cerca(e["margen_a_alerta"], -10.0, 1e-9))
c, out, err = correr("umbrales-alerta/scripts/umbrales.py", ej("umbrales-alerta", "series.csv"), ej("umbrales-alerta", "umbrales.csv"), "--json")
ok("corre sin error", c == 0, err.strip()[:200])
d = json.loads(out)
p = {x["punto"]: x for x in d["puntos"]}
ok("PC-01 en alerta desde noviembre, dos seguidas", p["PC-01"]["estado"] == "alerta" and p["PC-01"]["racha_alerta"] == 2 and p["PC-01"]["primera_superacion"] == "2025-11-15", str(p["PC-01"]["primera_superacion"]))
ok("QC-04 en accion, cuatro seguidas, primera superacion en mayo", p["QC-04"]["estado"] == "acción" and p["QC-04"]["racha_accion"] == 4 and p["QC-04"]["primera_superacion"] == "2025-05-15")
ok("PC-02 normal, PC-03 sin umbral, PC-05 sin datos", p["PC-02"]["estado"] == "normal" and p["PC-03"]["estado"] == "sin umbral" and p["PC-05"]["estado"] == "sin datos")
ok("los estados mas graves van primero", d["puntos"][0]["punto"] == "QC-04" and d["puntos"][1]["punto"] == "PC-01")
ok("la unidad de cada punto y el aviso de medicion igual al umbral", p["QC-04"]["unidad"] == "mg/L" and any("iguales al umbral" in x for x in p["PC-01"]["avisos"]) and not p["QC-04"]["avisos"])
e = evaluar([(datetime.date(2025, 1, 1), 8.0), (datetime.date(2025, 2, 1), 7.5)], 7.5, 7.0, "bajo", 1)
e2 = evaluar([(datetime.date(2025, 1, 1), 8.0), (datetime.date(2025, 2, 1), 7.5)], 7.5, 7.0, "bajo", 1, estricto=True)
ok("igual al umbral: cuenta por defecto y no cuenta en modo estricto", e["estado"] == "alerta" and e2["estado"] == "normal")
c, out, err = correr("umbrales-alerta/scripts/umbrales.py", ej("umbrales-alerta", "series.csv"), ej("umbrales-alerta", "umbrales.csv"), "--estricto", "--json")
pe = {x["punto"]: x for x in json.loads(out)["puntos"]}
ok("modo estricto: PC-01 sigue en alerta pero con una sola seguida y desde diciembre", c == 0 and pe["PC-01"]["estado"] == "alerta" and pe["PC-01"]["racha_alerta"] == 1 and pe["PC-01"]["primera_superacion"] == "2025-12-15")
c, out, err = correr("umbrales-alerta/scripts/umbrales.py", ej("umbrales-alerta", "series.csv"), ej("umbrales-alerta", "umbrales.csv"), "--consecutivas", "3")
ok("Markdown con 3 consecutivas: PC-01 en observacion", c == 0 and "| PC-01 | **en observación** |" in out and "| QC-04 | **acción** |" in out)
ok("la tabla muestra unidad y seguidas en accion", "| Seguidas en acción |" in out and "| mg/L |" in out and "| 8 | 4 | 2025-05-15 |" in out)

print("anonimizar-datos")
with tempfile.TemporaryDirectory() as tmp:
    clave, anon, vuelta = os.path.join(tmp, "clave.json"), os.path.join(tmp, "anon.csv"), os.path.join(tmp, "vuelta.csv")
    A = "anonimizar-datos/scripts/anonimizar.py"
    c, out, err = correr(A, ej("anonimizar-datos", "pozos.csv"), "--nombres", "punto", "--x", "este", "--y", "norte", "--clave", clave, "--salida", anon, "--json")
    ok("corre sin error", c == 0, err.strip()[:200])
    with open(anon, encoding="utf-8") as f:
        ta = f.read()
    ok("no queda ningun nombre real ni coordenada real", "Pozo" not in ta and "7405120" not in ta and "512340" not in ta and "P-001" in ta)
    filas = [l.split(",") for l in ta.strip().splitlines()[1:]]
    d12 = math.hypot(float(filas[0][1]) - float(filas[1][1]), float(filas[0][2]) - float(filas[1][2]))
    ok("las distancias entre pozos se conservan", cerca(d12, math.hypot(512980.00 - 512340.50, 7405610.75 - 7405120.25), 1e-9), f"{d12:.2f}")
    ok("los niveles no cambian", [f[3] for f in filas] == ["2301.42", "2302.10", "2298.76", "2300.05", "2296.31"])
    ok("el origen local parte en 1000", min(float(f[1]) for f in filas) == 1000.0 and min(float(f[2]) for f in filas) == 1000.0)
    c, out, err = correr(A, anon, "--revertir", "--clave", clave, "--x", "este", "--y", "norte", "--salida", vuelta, "--json")
    with open(vuelta, encoding="utf-8") as f, open(ej("anonimizar-datos", "pozos.csv"), encoding="utf-8") as g:
        ok("revertir devuelve el archivo original", c == 0 and f.read().strip() == g.read().strip())
    informe = os.path.join(tmp, "informe.md")
    with open(informe, "w", encoding="utf-8") as f:
        f.write("El nivel más bajo se midió en P-005 y el más alto en P-002.\n")
    c, out, err = correr(A, informe, "--revertir", "--clave", clave, "--salida", os.path.join(tmp, "informe-real.md"))
    with open(os.path.join(tmp, "informe-real.md"), encoding="utf-8") as f:
        ok("revierte codigos dentro de un texto", c == 0 and f.read().strip() == "El nivel más bajo se midió en Pozo Laguna y el más alto en Pozo Norte 2.")
    otro = os.path.join(tmp, "otro.csv")
    with open(otro, "w", encoding="utf-8") as f:
        f.write("punto;este;norte\nPozo Laguna;510890,00;7406250,40\nPozo Nuevo;511000,00;7406000,00\n")
    c, out, err = correr(A, otro, "--nombres", "punto", "--x", "este", "--y", "norte", "--clave", clave, "--json")
    with open(json.loads(out)["salida"], encoding="utf-8") as f:
        t2 = f.read()
    ok("la misma clave da el mismo codigo y el mismo origen en otro archivo", c == 0 and "P-005;1000,00;3270,40" in t2 and "P-006;1110,00;3020,00" in t2, t2.strip().replace("\n", " | "))

print("guia-acuifero")
r = subprocess.run([sys.executable, os.path.join(SK, "guia-acuifero", "scripts", "comprobar.py")], capture_output=True, text=True, encoding="utf-8",
                   env={k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")})
ok("el verificador de instalacion pasa completo", r.returncode == 0 and "Todo funciona" in r.stdout and "FALLA" not in r.stdout, (r.stdout + r.stderr).strip()[-200:])
r = subprocess.run([sys.executable, os.path.join(SK, "guia-acuifero", "scripts", "comprobar.py"), "--breve"], capture_output=True, text=True, encoding="utf-8")
ok("modo breve: una linea", r.returncode == 0 and r.stdout.strip().startswith("Comprobación: los 13 cálculos funcionan"), r.stdout.strip())

print()
if fallas:
    print(f"{len(fallas)} pruebas fallaron:")
    for f in fallas:
        print("  - " + f)
    sys.exit(1)
print("Todas las pruebas pasaron.")
