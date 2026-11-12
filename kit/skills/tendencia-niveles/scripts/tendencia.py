#!/usr/bin/env python3
"""Tendencias en series de monitoreo: Mann-Kendall, pendiente de Sen y valores anómalos.

Entrada: CSV en formato largo con columnas fecha, punto, valor.
Fechas AAAA-MM-DD, DD-MM-AAAA o DD/MM/AAAA. Acepta separador coma o punto y
coma, y coma decimal. Solo usa la biblioteca estándar de Python.

Ejemplos:
  python tendencia.py niveles.csv
  python tendencia.py calidad.csv --alfa 0.1 --json
"""
import argparse
import csv
import datetime as dt
import json
import math
import statistics
import sys

ALIAS = {
    "fecha": ("fecha", "date", "fecha_medicion", "fecha_muestreo"),
    "punto": ("punto", "pozo", "estacion", "estación", "id", "codigo", "código"),
    "valor": ("valor", "nivel", "nivel_m", "cota", "cota_msnm", "profundidad", "concentracion", "concentración"),
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
    if not v or v.startswith("<"):
        return None
    if delim != ",":
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def fecha(v):
    v = (v or "").strip().split(" ")[0].split("T")[0]
    for formato in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(v, formato).date()
        except ValueError:
            continue
    return None


def columna(filas, alias):
    for nombre in filas[0].keys():
        if nombre and nombre.strip().lower() in alias:
            return nombre
    return None


def mann_kendall(x):
    """Devuelve S, varianza, Z y valor p (dos colas), con corrección por empates."""
    n = len(x)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            d = x[j] - x[i]
            s += (d > 0) - (d < 0)
    empates = {}
    for v in x:
        empates[v] = empates.get(v, 0) + 1
    var = n * (n - 1) * (2 * n + 5)
    var -= sum(t * (t - 1) * (2 * t + 5) for t in empates.values() if t > 1)
    var /= 18.0
    if var <= 0:
        return s, var, 0.0, 1.0
    if s > 0:
        z = (s - 1) / math.sqrt(var)
    elif s < 0:
        z = (s + 1) / math.sqrt(var)
    else:
        z = 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    return s, var, z, p


def sen(t, x):
    """Pendiente de Sen: mediana de las pendientes entre todos los pares. t en años."""
    pend = []
    n = len(x)
    for i in range(n - 1):
        for j in range(i + 1, n):
            if t[j] != t[i]:
                pend.append((x[j] - x[i]) / (t[j] - t[i]))
    return statistics.median(pend) if pend else float("nan")


def anomalos(x, k=3.5):
    """Índices de valores alejados de la mediana más de k desviaciones robustas (MAD)."""
    if len(x) < 5:
        return []
    med = statistics.median(x)
    mad = statistics.median(abs(v - med) for v in x) * 1.4826
    if mad == 0:
        return []
    return [i for i, v in enumerate(x) if abs(v - med) / mad > k]


def analizar(punto, serie, alfa):
    serie = sorted(serie)
    fechas = [f for f, _ in serie]
    x = [v for _, v in serie]
    t = [(f - fechas[0]).days / 365.25 for f in fechas]
    r = {
        "punto": punto, "n": len(x),
        "desde": fechas[0].isoformat(), "hasta": fechas[-1].isoformat(),
        "minimo": min(x), "maximo": max(x), "media": statistics.fmean(x),
        "mediana": statistics.median(x),
    }
    if len(x) < 4:
        r.update({"tendencia": "datos insuficientes", "p": None, "z": None, "s": None, "sen_por_ano": None, "anomalos": []})
        return r
    s, _var, z, p = mann_kendall(x)
    pendiente = sen(t, x)
    if p < alfa and s > 0:
        tendencia = "creciente"
    elif p < alfa and s < 0:
        tendencia = "decreciente"
    else:
        tendencia = "sin tendencia"
    idx = anomalos(x)
    r.update({
        "s": s, "z": z, "p": p, "sen_por_ano": pendiente, "tendencia": tendencia,
        "cambio_total_estimado": pendiente * t[-1] if not math.isnan(pendiente) else None,
        "anomalos": [{"fecha": fechas[i].isoformat(), "valor": x[i]} for i in idx],
    })
    if len(x) < 10:
        r["aviso"] = "Menos de 10 datos: la prueba tiene poca potencia."
    return r


def fmt(v, cifras=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if abs(v) >= 100:
        return f"{v:.2f}"
    return f"{v:.{cifras}g}"


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Mann-Kendall, pendiente de Sen y valores anómalos por punto.")
    p.add_argument("csv", help="CSV con columnas fecha, punto, valor")
    p.add_argument("--alfa", type=float, default=0.05, help="Nivel de significancia (por defecto 0,05)")
    p.add_argument("--unidad", default="", help="Unidad del valor, solo para el encabezado (por ejemplo m o mg/L)")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    if not filas:
        raise SystemExit("El archivo no tiene datos.")
    cf, cp, cv = (columna(filas, ALIAS[k]) for k in ("fecha", "punto", "valor"))
    if not cf or not cv:
        raise SystemExit("No encuentro las columnas. Se esperan: fecha, punto, valor.")
    series = {}
    descartados = 0
    for f in filas:
        d = fecha(f[cf])
        v = numero(f[cv], delim)
        if d is None or v is None:
            descartados += 1
            continue
        series.setdefault((f[cp].strip() if cp else "serie"), []).append((d, v))
    if not series:
        raise SystemExit("No hay filas con fecha y valor válidos.")
    res = [analizar(pt, s, a.alfa) for pt, s in sorted(series.items())]

    if a.json:
        print(json.dumps({"alfa": a.alfa, "filas_descartadas": descartados, "puntos": res}, ensure_ascii=False, indent=2))
        return 0

    u = f" ({a.unidad})" if a.unidad else ""
    upa = f"{a.unidad}/año" if a.unidad else "por año"
    print(f"# Tendencias: {a.csv}\n")
    print(f"| Punto | n | Desde | Hasta | Mín{u} | Máx{u} | Mediana{u} | Sen ({upa}) | Z | p | Tendencia |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res:
        print(f"| {r['punto']} | {r['n']} | {r['desde']} | {r['hasta']} | {fmt(r['minimo'])} | {fmt(r['maximo'])} | "
              f"{fmt(r['mediana'])} | {fmt(r['sen_por_ano'], 3)} | {fmt(r['z'], 3)} | {fmt(r['p'], 2)} | {r['tendencia']} |")
    notas = []
    for r in res:
        for an in r.get("anomalos", []):
            notas.append(f"- **{r['punto']}**: valor anómalo {fmt(an['valor'])} el {an['fecha']} (revisar antes de usar).")
        if r.get("aviso"):
            notas.append(f"- **{r['punto']}**: {r['aviso']}")
    if notas:
        print("\n## Observaciones\n")
        print("\n".join(notas))
    if descartados:
        print(f"\nSe descartaron {descartados} filas sin fecha o sin valor numérico (incluye valores bajo el límite de detección).")
    print(f"\nPrueba de Mann-Kendall de dos colas con α = {a.alfa:g}. La pendiente de Sen es la mediana de las pendientes entre pares. "
          "La prueba no corrige estacionalidad ni autocorrelación: con datos mensuales, compara además por estación del año.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
