#!/usr/bin/env python3
"""Vista rápida de piezometría: interpolación, curvas de nivel y gradiente regional.

Entrada: CSV con columnas punto, x, y, nivel (cota piezométrica en m s. n. m.).
Si en vez de nivel trae cota y profundidad, calcula nivel = cota − profundidad.
Coordenadas proyectadas en metros (por ejemplo UTM). Acepta separador coma o
punto y coma, y coma decimal. Solo usa la biblioteca estándar de Python.

Salidas en la carpeta indicada:
  curvas.geojson  curvas piezométricas (se abren en QGIS)
  grilla.asc      superficie interpolada en formato ASCII de ESRI
  vista.svg       vista previa con pozos, curvas y dirección de flujo

Ejemplo:
  python piezometria.py niveles.csv --intervalo 5 --epsg 32719 --salida piezometria
"""
import argparse
import csv
import json
import math
import os
import sys

ALIAS = {
    "punto": ("punto", "pozo", "id", "nombre", "codigo", "código"),
    "x": ("x", "este", "este_m", "e", "utm_e", "easting"),
    "y": ("y", "norte", "norte_m", "n", "utm_n", "northing"),
    "nivel": ("nivel", "nivel_msnm", "cota_piezometrica", "cota_piezométrica", "h", "carga"),
    "cota": ("cota", "cota_msnm", "cota_terreno", "cota_referencia", "z"),
    "profundidad": ("profundidad", "profundidad_m", "prof_nivel", "nivel_estatico", "nivel_estático", "ne"),
}


def leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        lineas = [l for l in f.read().splitlines() if l.strip()]
    if not lineas:
        raise SystemExit("El archivo está vacío: " + ruta)
    cab = lineas[0]
    if cab.count(";") > cab.count(","):
        delim = ";"
    elif "\t" in cab and "," not in cab:
        delim = "\t"
    else:
        delim = ","
    return list(csv.DictReader(lineas, delimiter=delim)), delim


def numero(v, delim):
    v = (v or "").strip()
    if not v:
        return None
    if delim != ",":
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def columna(filas, alias):
    for nombre in filas[0].keys():
        if nombre and nombre.strip().lower() in alias:
            return nombre
    return None


def cargar(ruta):
    filas, delim = leer_csv(ruta)
    if not filas:
        raise SystemExit("El archivo no tiene puntos.")
    c = {k: columna(filas, v) for k, v in ALIAS.items()}
    if not c["x"] or not c["y"]:
        raise SystemExit("No encuentro las columnas de coordenadas (x, y o este, norte).")
    if not c["nivel"] and not (c["cota"] and c["profundidad"]):
        raise SystemExit("Falta la columna nivel (o bien cota y profundidad).")
    puntos = []
    for i, f in enumerate(filas):
        x, y = numero(f[c["x"]], delim), numero(f[c["y"]], delim)
        if c["nivel"]:
            h = numero(f[c["nivel"]], delim)
        else:
            cota, prof = numero(f[c["cota"]], delim), numero(f[c["profundidad"]], delim)
            h = cota - prof if cota is not None and prof is not None else None
        if x is None or y is None or h is None:
            continue
        nombre = (f[c["punto"]].strip() if c["punto"] else "") or f"P{i + 1}"
        puntos.append((nombre, x, y, h))
    if len(puntos) < 3:
        raise SystemExit("Se necesitan al menos 3 puntos con coordenadas y nivel.")
    return puntos


def plano(puntos):
    """Ajusta h = a·x + b·y + c por mínimos cuadrados. Devuelve gradiente, azimut del flujo y R²."""
    n = len(puntos)
    mx = sum(p[1] for p in puntos) / n
    my = sum(p[2] for p in puntos) / n
    mh = sum(p[3] for p in puntos) / n
    sxx = sum((p[1] - mx) ** 2 for p in puntos)
    syy = sum((p[2] - my) ** 2 for p in puntos)
    sxy = sum((p[1] - mx) * (p[2] - my) for p in puntos)
    sxh = sum((p[1] - mx) * (p[3] - mh) for p in puntos)
    syh = sum((p[2] - my) * (p[3] - mh) for p in puntos)
    det = sxx * syy - sxy ** 2
    if abs(det) < 1e-9 * max(sxx * syy, 1e-30):
        return None
    a = (sxh * syy - syh * sxy) / det
    b = (syh * sxx - sxh * sxy) / det
    ss_res = sum((p[3] - mh - a * (p[1] - mx) - b * (p[2] - my)) ** 2 for p in puntos)
    ss_tot = sum((p[3] - mh) ** 2 for p in puntos)
    grad = math.hypot(a, b)
    azimut = math.degrees(math.atan2(-a, -b)) % 360.0 if grad > 0 else None
    return {"gradiente": grad, "azimut_flujo": azimut, "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "a": a, "b": b}


def rumbo(az):
    if az is None:
        return "—"
    nombres = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
    return nombres[int((az + 11.25) // 22.5) % 16]


def interpolar(puntos, celda=None, margen=0.1, potencia=2.0, max_celdas=120):
    xs = [p[1] for p in puntos]
    ys = [p[2] for p in puntos]
    ancho = max(xs) - min(xs)
    alto = max(ys) - min(ys)
    lado = max(ancho, alto)
    if lado == 0:
        raise SystemExit("Todos los puntos tienen la misma coordenada.")
    m = lado * margen
    x0, y0 = min(xs) - m, min(ys) - m
    x1, y1 = max(xs) + m, max(ys) + m
    if not celda:
        celda = max(x1 - x0, y1 - y0) / 80.0
    nx = int(math.ceil((x1 - x0) / celda)) + 1
    ny = int(math.ceil((y1 - y0) / celda)) + 1
    if max(nx, ny) > max_celdas * 4:
        raise SystemExit(f"La grilla tendría {nx}×{ny} celdas. Usa un tamaño de celda mayor con --celda.")
    grilla = []
    for j in range(ny):
        y = y0 + j * celda
        fila = []
        for i in range(nx):
            x = x0 + i * celda
            num = den = 0.0
            exacto = None
            for _, px, py, h in puntos:
                d2 = (x - px) ** 2 + (y - py) ** 2
                if d2 < 1e-12:
                    exacto = h
                    break
                w = 1.0 / d2 ** (potencia / 2.0)
                num += w * h
                den += w
            fila.append(exacto if exacto is not None else num / den)
        grilla.append(fila)
    return {"x0": x0, "y0": y0, "celda": celda, "nx": nx, "ny": ny, "z": grilla}


def curvas(g, niveles):
    """Curvas de nivel por «marching squares». Devuelve {nivel: [polilíneas]}."""
    x0, y0, c, nx, ny, z = g["x0"], g["y0"], g["celda"], g["nx"], g["ny"], g["z"]

    def cruce(pa, va, pb, vb, nivel):
        t = (nivel - va) / (vb - va) if vb != va else 0.5
        return (pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1]))

    resultado = {}
    original = z
    for nivel in niveles:
        # Si un nodo vale exactamente el nivel, se desplaza una fracción mínima para que
        # la curva no pase justo por el nodo (evita segmentos nulos y líneas cortadas)
        eps = 1e-9 * max(1.0, abs(nivel))
        z = [[v + eps if v == nivel else v for v in fila] for fila in original]
        segmentos = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                bl, br = z[j][i], z[j][i + 1]
                tl, tr = z[j + 1][i], z[j + 1][i + 1]
                caso = (bl >= nivel) | ((br >= nivel) << 1) | ((tr >= nivel) << 2) | ((tl >= nivel) << 3)
                if caso in (0, 15):
                    continue
                pbl = (x0 + i * c, y0 + j * c)
                pbr = (x0 + (i + 1) * c, y0 + j * c)
                ptl = (x0 + i * c, y0 + (j + 1) * c)
                ptr = (x0 + (i + 1) * c, y0 + (j + 1) * c)
                # Cada lado se calcula siempre en el mismo sentido para que los extremos coincidan
                aba = lambda: cruce(pbl, bl, pbr, br, nivel)
                der = lambda: cruce(pbr, br, ptr, tr, nivel)
                arr = lambda: cruce(ptl, tl, ptr, tr, nivel)
                izq = lambda: cruce(pbl, bl, ptl, tl, nivel)
                centro = (bl + br + tl + tr) / 4.0 >= nivel
                tabla = {
                    1: [(izq, aba)], 2: [(aba, der)], 3: [(izq, der)], 4: [(der, arr)],
                    5: [(izq, arr), (aba, der)] if centro else [(izq, aba), (der, arr)],
                    6: [(aba, arr)], 7: [(izq, arr)], 8: [(izq, arr)], 9: [(aba, arr)],
                    10: [(izq, aba), (der, arr)] if centro else [(izq, arr), (aba, der)],
                    11: [(der, arr)], 12: [(izq, der)], 13: [(aba, der)], 14: [(izq, aba)],
                }
                for f1, f2 in tabla[caso]:
                    p1, p2 = f1(), f2()
                    if abs(p1[0] - p2[0]) > 1e-9 or abs(p1[1] - p2[1]) > 1e-9:
                        segmentos.append((p1, p2))
        if segmentos:
            resultado[nivel] = unir(segmentos)
    return resultado


def unir(segmentos):
    """Encadena segmentos sueltos en polilíneas."""
    def clave(p):
        return (round(p[0], 4), round(p[1], 4))

    segmentos = [sg for sg in segmentos if clave(sg[0]) != clave(sg[1])]
    vecinos = {}
    for idx, (a, b) in enumerate(segmentos):
        vecinos.setdefault(clave(a), []).append(idx)
        vecinos.setdefault(clave(b), []).append(idx)
    usado = [False] * len(segmentos)
    lineas = []
    for i in range(len(segmentos)):
        if usado[i]:
            continue
        usado[i] = True
        linea = [segmentos[i][0], segmentos[i][1]]
        for al_final in (True, False):
            while True:
                extremo = linea[-1] if al_final else linea[0]
                sig = next((j for j in vecinos.get(clave(extremo), []) if not usado[j]), None)
                if sig is None:
                    break
                usado[sig] = True
                a, b = segmentos[sig]
                otro = b if clave(a) == clave(extremo) else a
                if al_final:
                    linea.append(otro)
                else:
                    linea.insert(0, otro)
        lineas.append(linea)
    return lineas


def niveles_curvas(puntos, intervalo):
    hs = [p[3] for p in puntos]
    if not intervalo:
        rango = max(hs) - min(hs)
        if rango == 0:
            return [], 0
        bruto = rango / 8.0
        base = 10 ** math.floor(math.log10(bruto))
        intervalo = min((m * base for m in (1, 2, 5, 10)), key=lambda v: abs(v - bruto))
    primero = math.ceil(min(hs) / intervalo) * intervalo
    out = []
    v = primero
    while v <= max(hs) + 1e-9:
        out.append(round(v, 6))
        v += intervalo
    return out, intervalo


def guardar_geojson(ruta, cv, epsg):
    feats = []
    for nivel, lineas in sorted(cv.items()):
        feats.append({"type": "Feature", "properties": {"nivel": nivel},
                      "geometry": {"type": "MultiLineString",
                                   "coordinates": [[[round(x, 2), round(y, 2)] for x, y in l] for l in lineas]}})
    fc = {"type": "FeatureCollection", "name": "curvas_piezometricas", "features": feats}
    if epsg:
        fc["crs"] = {"type": "name", "properties": {"name": f"urn:ogc:def:crs:EPSG::{epsg}"}}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)


def guardar_asc(ruta, g):
    with open(ruta, "w", encoding="ascii") as f:
        f.write(f"ncols {g['nx']}\nnrows {g['ny']}\n")
        f.write(f"xllcenter {g['x0']:.3f}\nyllcenter {g['y0']:.3f}\n")
        f.write(f"cellsize {g['celda']:.3f}\nNODATA_value -9999\n")
        for fila in reversed(g["z"]):
            f.write(" ".join(f"{v:.3f}" for v in fila) + "\n")


def guardar_svg(ruta, puntos, g, cv, pl):
    W = 820.0
    x0, y0 = g["x0"], g["y0"]
    ancho = (g["nx"] - 1) * g["celda"]
    alto = (g["ny"] - 1) * g["celda"]
    esc = (W - 40) / ancho
    H = alto * esc + 40

    def P(x, y):
        return 20 + (x - x0) * esc, H - 20 - (y - y0) * esc

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
         'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="11">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
         f'<rect x="20" y="20" width="{W - 40:.0f}" height="{H - 40:.0f}" fill="#fbfbfd" stroke="#d2d2d7"/>']
    for nivel, lineas in sorted(cv.items()):
        for l in lineas:
            d = " ".join(("M" if k == 0 else "L") + f"{P(*p)[0]:.1f} {P(*p)[1]:.1f}" for k, p in enumerate(l))
            o.append(f'<path d="{d}" fill="none" stroke="#0071e3" stroke-width="1.2"/>')
        largo = max(lineas, key=len)
        mx, my = P(*largo[len(largo) // 2])
        o.append(f'<text x="{mx:.1f}" y="{my - 3:.1f}" fill="#0071e3" text-anchor="middle" '
                 f'paint-order="stroke" stroke="#fbfbfd" stroke-width="3">{nivel:g}</text>')
    for nombre, x, y, h in puntos:
        px, py = P(x, y)
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="#1d1d1f"/>')
        o.append(f'<text x="{px + 6:.1f}" y="{py - 5:.1f}" fill="#1d1d1f" paint-order="stroke" stroke="#fbfbfd" '
                 f'stroke-width="3">{nombre} · {h:g}</text>')
    if pl and pl["azimut_flujo"] is not None:
        az = math.radians(pl["azimut_flujo"])
        cx, cy = W - 70, 70
        dx, dy = 28 * math.sin(az), -28 * math.cos(az)
        o.append(f'<circle cx="{cx}" cy="{cy}" r="36" fill="#fff" stroke="#d2d2d7"/>')
        o.append(f'<line x1="{cx - dx:.1f}" y1="{cy - dy:.1f}" x2="{cx + dx:.1f}" y2="{cy + dy:.1f}" stroke="#ff3b30" stroke-width="2.5" stroke-linecap="round"/>')
        o.append(f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="4.5" fill="#ff3b30"/>')
        o.append(f'<text x="{cx}" y="{cy + 52}" text-anchor="middle" fill="#6e6e73">flujo {pl["azimut_flujo"]:.0f}° ({rumbo(pl["azimut_flujo"])})</text>')
        o.append(f'<text x="{cx}" y="{cy - 42}" text-anchor="middle" fill="#6e6e73">N</text>')
    o.append("</svg>")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(o))


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Curvas piezométricas rápidas y gradiente regional.")
    p.add_argument("csv", help="CSV con punto, x, y, nivel")
    p.add_argument("--intervalo", type=float, default=None, help="Equidistancia de las curvas en m (por defecto, automática)")
    p.add_argument("--celda", type=float, default=None, help="Tamaño de celda de la grilla en m (por defecto, automático)")
    p.add_argument("--potencia", type=float, default=2.0, help="Exponente de la distancia inversa (por defecto 2)")
    p.add_argument("--epsg", type=int, default=None, help="Código EPSG de las coordenadas, para etiquetar el GeoJSON")
    p.add_argument("--salida", default=None, help="Carpeta donde guardar curvas.geojson, grilla.asc y vista.svg")
    p.add_argument("--json", action="store_true", help="Resumen en JSON")
    a = p.parse_args(argv)

    puntos = cargar(a.csv)
    pl = plano(puntos)
    g = interpolar(puntos, a.celda, potencia=a.potencia)
    niveles, intervalo = niveles_curvas(puntos, a.intervalo)
    cv = curvas(g, niveles)
    archivos = []
    if a.salida:
        os.makedirs(a.salida, exist_ok=True)
        guardar_geojson(os.path.join(a.salida, "curvas.geojson"), cv, a.epsg)
        guardar_asc(os.path.join(a.salida, "grilla.asc"), g)
        guardar_svg(os.path.join(a.salida, "vista.svg"), puntos, g, cv, pl)
        archivos = [os.path.join(a.salida, n) for n in ("curvas.geojson", "grilla.asc", "vista.svg")]

    hs = [q[3] for q in puntos]
    resumen = {
        "puntos": len(puntos), "nivel_minimo": min(hs), "nivel_maximo": max(hs),
        "gradiente_regional": pl["gradiente"] if pl else None,
        "azimut_flujo_grados": pl["azimut_flujo"] if pl else None,
        "rumbo_flujo": rumbo(pl["azimut_flujo"]) if pl else None,
        "r2_plano": pl["r2"] if pl else None,
        "intervalo_curvas_m": intervalo, "curvas": sorted(cv.keys()),
        "celda_m": g["celda"], "grilla": [g["nx"], g["ny"]], "archivos": archivos,
    }
    if a.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return 0

    print(f"# Piezometría: {a.csv}\n")
    print(f"- Puntos: {len(puntos)} · Nivel entre {min(hs):g} y {max(hs):g} m s. n. m.")
    if pl:
        print(f"- Gradiente regional (plano ajustado): {pl['gradiente']:.4g} m/m = {pl['gradiente'] * 100:.3g} %")
        print(f"- Dirección de flujo: {pl['azimut_flujo']:.0f}° desde el norte ({rumbo(pl['azimut_flujo'])}) · R² del plano: {pl['r2']:.3f}")
        if pl["r2"] < 0.8:
            print("  El plano explica poco la piezometría: hay curvatura, bombeo o más de un sistema. No uses un único gradiente.")
    else:
        print("- Los puntos están alineados: no se puede ajustar un plano.")
    print(f"- Curvas cada {intervalo:g} m: {', '.join(f'{v:g}' for v in sorted(cv.keys())) or 'ninguna'}")
    print(f"- Grilla de {g['nx']}×{g['ny']} celdas de {g['celda']:.4g} m")
    if archivos:
        print("\nArchivos:\n" + "\n".join("- " + r for r in archivos))
    print("\nLa superficie se interpola por distancia inversa: sirve para mirar los datos, no como mapa final. "
          "Ajusta las curvas con criterio hidrogeológico (bordes, ríos, bombeo, unidades distintas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
