#!/usr/bin/env python3
"""Dos cálculos frecuentes en salares: carga equivalente de agua dulce y curva de evaporación.

1) carga: convierte niveles medidos en aguas de distinta densidad a carga equivalente de agua dulce.
   CSV: punto, nivel, cota_filtro, densidad
     nivel        cota del nivel medido en el pozo (m s. n. m.)
     cota_filtro  cota del punto medio del tramo captado (m s. n. m.)
     densidad     del agua del pozo, en kg/m3 o en g/cm3
   h_dulce = cota_filtro + (densidad / densidad_dulce) × (nivel − cota_filtro)

2) evaporacion: ajusta E = E0 × exp(−k × z) a mediciones de evaporación contra profundidad del nivel.
   CSV: punto, profundidad, evaporacion
     profundidad  del nivel freático bajo la superficie (m)
     evaporacion  medida (mm/d)

Acepta separador coma o punto y coma, y coma decimal. Solo biblioteca estándar.

Ejemplos:
  python salares.py carga niveles.csv
  python salares.py evaporacion evaporacion.csv --json
"""
import argparse
import csv
import json
import math
import sys

ALIAS = {
    "punto": ("punto", "pozo", "id", "nombre", "codigo", "código"),
    "nivel": ("nivel", "nivel_msnm", "cota_nivel", "h"),
    "filtro": ("cota_filtro", "cota_rejilla", "cota_tramo", "z", "cota_medio_filtro", "cota_criba"),
    "densidad": ("densidad", "density", "rho"),
    "profundidad": ("profundidad", "profundidad_m", "prof", "z_nivel", "profundidad_nivel"),
    "evaporacion": ("evaporacion", "evaporación", "evap", "e", "evaporacion_mm_d", "tasa"),
    "superficie": ("superficie", "tipo_superficie", "tipo", "cobertura"),
}


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


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


def carga_equivalente(nivel, cota_filtro, densidad, densidad_dulce=1000.0):
    """Carga equivalente de agua dulce (m). La densidad puede venir en kg/m3 o en g/cm3."""
    if densidad < 5:
        densidad *= 1000.0
    return cota_filtro + (densidad / densidad_dulce) * (nivel - cota_filtro)


def ajustar_evaporacion(prof, evap):
    """Ajuste log-lineal de E = E0·exp(−k·z). Devuelve E0, k, R² y profundidad al 1 % de E0."""
    pares = [(z, e) for z, e in zip(prof, evap) if e > 0 and z >= 0]
    if len(pares) < 3:
        return None
    n = len(pares)
    xs = [z for z, _ in pares]
    ys = [math.log(e) for _, e in pares]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a0 = my - b * mx
    ss_res = sum((y - (a0 + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    k = -b
    return {"E0_mm_d": math.exp(a0), "k_por_m": k, "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "profundidad_1pct_m": math.log(100.0) / k if k > 0 else None, "puntos": n,
            "profundidad_min_m": min(xs), "profundidad_max_m": max(xs)}


def cmd_carga(a):
    filas, delim = leer_csv(a.csv)
    c = {k: columna(filas, ALIAS[k]) for k in ("punto", "nivel", "filtro", "densidad")}
    if not c["nivel"] or not c["filtro"] or not c["densidad"]:
        raise SystemExit("No encuentro las columnas. Se esperan: punto, nivel, cota_filtro, densidad.")
    res, omitidos = [], []
    for i, f in enumerate(filas):
        nombre = (f[c["punto"]].strip() if c["punto"] else "") or f"fila {i + 2}"
        h, z, d = (numero(f[c[k]], delim) for k in ("nivel", "filtro", "densidad"))
        if h is None or z is None or d is None:
            omitidos.append(nombre)
            continue
        rho = d * 1000.0 if d < 5 else d
        hf = carga_equivalente(h, z, rho, a.densidad_dulce)
        aviso = "densidad leída como g/cm3 y convertida a kg/m3" if d < 5 else ""
        if not (950 <= rho <= 1400):
            aviso = "densidad fuera del rango habitual (950 a 1400 kg/m3): revisa la unidad"
        elif z > h:
            aviso = "la cota del tramo captado está sobre el nivel: revisa los datos"
        res.append({"punto": nombre, "nivel": h, "cota_filtro": z, "densidad_kg_m3": rho, "carga_equivalente": hf,
                    "diferencia": hf - h, "aviso": aviso})
    if not res:
        raise SystemExit("Ningún punto tiene nivel, cota del tramo captado y densidad.")
    cotas = [r["cota_filtro"] for r in res]
    dispersion = max(cotas) - min(cotas)
    generales = []
    if dispersion > a.tolerancia_cota:
        generales.append(f"Los tramos captados difieren hasta {dispersion:.1f} m en cota. La comparación en horizontal solo es directa entre pozos "
                         "que captan a cota similar; entre los demás queda un término de flotación sin corregir.")
    if a.json:
        print(json.dumps({"densidad_dulce_kg_m3": a.densidad_dulce, "puntos": res, "omitidos": omitidos,
                          "dispersion_cota_filtro_m": dispersion, "avisos": generales}, ensure_ascii=False, indent=2))
        return 0
    print(f"# Carga equivalente de agua dulce: {a.csv}\n")
    print("| Punto | Nivel medido (m s. n. m.) | Cota del tramo captado | Densidad (kg/m³) | Carga equivalente (m s. n. m.) | Diferencia (m) |")
    print("|---|---|---|---|---|---|")
    for r in res:
        print(f"| {r['punto']} | {r['nivel']:.2f} | {r['cota_filtro']:.2f} | {r['densidad_kg_m3']:.0f} | "
              f"{r['carga_equivalente']:.2f} | {r['diferencia']:+.2f} |")
    notas = [r for r in res if r["aviso"]]
    if notas or omitidos or generales:
        print("\n## Observaciones\n")
        for g in generales:
            print("- " + g)
        for r in notas:
            print(f"- **{r['punto']}**: {r['aviso']}.")
        if omitidos:
            print("- Sin nivel, cota del tramo captado o densidad, no calculados: " + ", ".join(omitidos) + ".")
    print(f"\nh_dulce = z + (ρ/ρ_dulce) × (h − z), con ρ_dulce = {a.densidad_dulce:g} kg/m³ y z la cota del punto medio del tramo captado. "
          "Sirve para comparar niveles en horizontal entre pozos de distinta densidad que captan a cota similar. Supone densidad uniforme "
          "en la columna de agua del pozo. Para gradientes verticales, o entre pozos que captan a cotas muy distintas, hace falta otro "
          "tratamiento: no uses estas cargas directamente.")
    return 0


def cmd_evaporacion(a):
    filas, delim = leer_csv(a.csv)
    c = {k: columna(filas, ALIAS[k]) for k in ("punto", "profundidad", "evaporacion")}
    if not c["profundidad"] or not c["evaporacion"]:
        raise SystemExit("No encuentro las columnas. Se esperan: punto, profundidad, evaporacion.")
    cs = columna(filas, ALIAS["superficie"])
    prof, evap, grupos = [], [], {}
    for f in filas:
        z, e = numero(f[c["profundidad"]], delim), numero(f[c["evaporacion"]], delim)
        if z is not None and e is not None:
            prof.append(z)
            evap.append(e)
            if cs and (f[cs] or "").strip():
                g = grupos.setdefault(f[cs].strip().lower(), ([], []))
                g[0].append(z)
                g[1].append(e)
    por_superficie = {}
    for nombre, (pz, pe) in sorted(grupos.items()):
        aj = ajustar_evaporacion(pz, pe)
        por_superficie[nombre] = aj if aj else {"puntos": len(pz), "nota": "menos de 3 mediciones útiles: sin ajuste"}
    r = ajustar_evaporacion(prof, evap)
    if not r:
        raise SystemExit("Se necesitan al menos 3 mediciones con evaporación mayor que cero y profundidades distintas.")
    avisos = []
    if not grupos:
        avisos.append("El archivo no indica el tipo de superficie (columna «superficie»): si mezcla costra, suelo, vegetación o agua libre, ajusta cada uno por separado.")
    elif len(grupos) > 1:
        avisos.append("Hay más de un tipo de superficie: usa los ajustes por superficie; el ajuste global mezcla tipos y solo sirve de referencia.")
    if r["k_por_m"] <= 0:
        avisos.append("La evaporación no disminuye con la profundidad en estos datos: el modelo exponencial no aplica.")
    if r["r2"] < 0.7:
        avisos.append(f"R² = {r['r2']:.2f}: mucha dispersión. Separa por tipo de superficie (costra, suelo, vegetación) antes de ajustar.")
    if r["puntos"] < 6:
        avisos.append("Menos de 6 mediciones: el ajuste es poco robusto.")
    if r["profundidad_1pct_m"] and r["profundidad_1pct_m"] > 2 * r["profundidad_max_m"]:
        avisos.append("La profundidad de extinción queda muy fuera del rango medido: es una extrapolación.")
    nulos = sum(1 for e in evap if e <= 0)
    if nulos:
        avisos.append(f"{nulos} mediciones con evaporación nula quedaron fuera del ajuste logarítmico.")
    if a.json:
        print(json.dumps({"ajuste": r, "por_superficie": por_superficie, "avisos": avisos}, ensure_ascii=False, indent=2))
        return 0
    print(f"# Curva de evaporación: {a.csv}\n")
    print(f"- Mediciones usadas: {r['puntos']}, entre {r['profundidad_min_m']:g} y {r['profundidad_max_m']:g} m de profundidad del nivel.")
    print(f"- Evaporación en superficie, E₀: {r['E0_mm_d']:.3g} mm/d ({r['E0_mm_d'] * 365.25:.0f} mm/año).")
    print(f"- Coeficiente de decaimiento, k: {r['k_por_m']:.3g} por metro. R² = {r['r2']:.3f}.")
    if r["profundidad_1pct_m"]:
        print(f"- La evaporación cae al 1 % de E₀ a {r['profundidad_1pct_m']:.2g} m de profundidad.")
    print("\n| Profundidad del nivel (m) | Evaporación estimada (mm/d) |\n|---|---|")
    for z in (0, 0.25, 0.5, 1, 1.5, 2, 3):
        print(f"| {z:g} | {r['E0_mm_d'] * math.exp(-r['k_por_m'] * z):.3g} |")
    if len(por_superficie) > 1 or (len(por_superficie) == 1 and len(grupos) == 1):
        print("\n## Por tipo de superficie\n\n| Superficie | Mediciones | E₀ (mm/d) | k (por metro) | R² | Profundidad al 1 % (m) |\n|---|---|---|---|---|---|")
        for nombre, aj in por_superficie.items():
            if "E0_mm_d" not in aj:
                print(f"| {nombre} | {aj['puntos']} | — | — | — | {aj['nota']} |")
                continue
            ext = f"{aj['profundidad_1pct_m']:.2g}" if aj["profundidad_1pct_m"] else "—"
            print(f"| {nombre} | {aj['puntos']} | {aj['E0_mm_d']:.3g} | {aj['k_por_m']:.3g} | {aj['r2']:.3f} | {ext} |")
    if avisos:
        print("\n## Lectura\n")
        for av in avisos:
            print("- " + av)
    print("\nE = E₀ × exp(−k × z), ajustado por regresión sobre el logaritmo de la evaporación. Es un modelo empírico: "
          "informa el rango de profundidades medido y no extrapoles sin decirlo.")
    return 0


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Carga equivalente de agua dulce y curva de evaporación en salares.")
    sub = p.add_subparsers(dest="orden", required=True)
    pc = sub.add_parser("carga", help="Carga equivalente de agua dulce")
    pc.add_argument("csv")
    pc.add_argument("--densidad-dulce", type=float, default=1000.0, help="Densidad de referencia en kg/m3 (por defecto 1000)")
    pc.add_argument("--tolerancia-cota", type=float, default=10.0, help="Diferencia de cota entre tramos captados sobre la cual se avisa (por defecto 10 m)")
    pc.add_argument("--json", action="store_true")
    pc.set_defaults(func=cmd_carga)
    pe = sub.add_parser("evaporacion", help="Ajuste de la curva de evaporación contra profundidad")
    pe.add_argument("csv")
    pe.add_argument("--json", action="store_true")
    pe.set_defaults(func=cmd_evaporacion)
    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
