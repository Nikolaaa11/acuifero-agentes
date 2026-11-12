#!/usr/bin/env python3
"""Estadísticos de calibración de un modelo de flujo: observado contra simulado.

Entrada: CSV con columnas punto, observado, simulado y, si se quiere, grupo
(capa, zona o tipo de dato). Acepta separador coma o punto y coma, y coma
decimal. Solo usa la biblioteca estándar de Python.

Residual = simulado − observado (positivo: el modelo sobreestima).

Ejemplos:
  python calibracion.py niveles.csv
  python calibracion.py niveles.csv --umbral 5 --json
"""
import argparse
import csv
import json
import math
import sys

ALIAS = {
    "punto": ("punto", "pozo", "id", "nombre", "objetivo", "target"),
    "obs": ("observado", "obs", "medido", "nivel_observado", "observed"),
    "sim": ("simulado", "sim", "calculado", "nivel_simulado", "simulated", "modelado"),
    "grupo": ("grupo", "capa", "zona", "tipo", "layer"),
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


def estadisticos(pares):
    """pares: lista de (observado, simulado)."""
    n = len(pares)
    res = [s - o for o, s in pares]
    obs = [o for o, _ in pares]
    sim = [s for _, s in pares]
    me = sum(res) / n
    mae = sum(abs(r) for r in res) / n
    rmse = math.sqrt(sum(r * r for r in res) / n)
    rango = max(obs) - min(obs)
    mo, ms = sum(obs) / n, sum(sim) / n
    so = sum((o - mo) ** 2 for o in obs)
    ss = sum((s - ms) ** 2 for s in sim)
    cov = sum((o - mo) * (s - ms) for o, s in pares)
    r2 = cov ** 2 / (so * ss) if so > 0 and ss > 0 else float("nan")
    return {
        "n": n, "error_medio": me, "error_medio_absoluto": mae, "rmse": rmse,
        "rango_observado": rango,
        "rmse_normalizado_pct": 100.0 * rmse / rango if rango > 0 else float("nan"),
        "mae_normalizado_pct": 100.0 * mae / rango if rango > 0 else float("nan"),
        "r2": r2, "residual_minimo": min(res), "residual_maximo": max(res),
        "sobreestimados": sum(1 for r in res if r > 0), "subestimados": sum(1 for r in res if r < 0),
    }


def fmt(v, c=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if abs(v) >= 10 ** c:
        return f"{v:.0f}"
    return f"{v:.{c}g}"


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Estadísticos de calibración (observado contra simulado).")
    p.add_argument("csv", help="CSV con punto, observado, simulado y, opcional, grupo")
    p.add_argument("--umbral", type=float, default=10.0, help="RMSE normalizado de referencia en %% (por defecto 10)")
    p.add_argument("--peores", type=int, default=5, help="Cuántos residuales mayores listar (por defecto 5)")
    p.add_argument("--unidad", default="m", help="Unidad de los datos (por defecto m)")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    if not filas:
        raise SystemExit("El archivo no tiene datos.")
    c = {k: columna(filas, v) for k, v in ALIAS.items()}
    if not c["obs"] or not c["sim"]:
        raise SystemExit("No encuentro las columnas. Se esperan: punto, observado, simulado (y opcional grupo).")
    datos = []
    for i, f in enumerate(filas):
        o, s = numero(f[c["obs"]], delim), numero(f[c["sim"]], delim)
        if o is None or s is None:
            continue
        datos.append({"punto": (f[c["punto"]].strip() if c["punto"] else f"fila {i + 2}"),
                      "grupo": (f[c["grupo"]].strip() if c["grupo"] else ""), "obs": o, "sim": s, "res": s - o})
    if len(datos) < 2:
        raise SystemExit("Se necesitan al menos 2 pares observado-simulado.")

    total = estadisticos([(d["obs"], d["sim"]) for d in datos])
    grupos = {}
    for d in datos:
        if d["grupo"]:
            grupos.setdefault(d["grupo"], []).append((d["obs"], d["sim"]))
    por_grupo = {g: estadisticos(v) for g, v in sorted(grupos.items()) if len(v) >= 2}
    peores = sorted(datos, key=lambda d: abs(d["res"]), reverse=True)[: a.peores]

    avisos = []
    nr = total["rmse_normalizado_pct"]
    if not math.isnan(nr):
        if nr <= a.umbral:
            avisos.append(f"RMSE normalizado {nr:.1f} %: dentro de la referencia de {a.umbral:g} %.")
        else:
            avisos.append(f"RMSE normalizado {nr:.1f} %: sobre la referencia de {a.umbral:g} %.")
    if total["rmse"] > 0 and abs(total["error_medio"]) > 0.5 * total["rmse"]:
        sentido = "sobreestima" if total["error_medio"] > 0 else "subestima"
        avisos.append(f"Sesgo: el modelo {sentido} de forma sistemática (error medio {fmt(total['error_medio'])} {a.unidad}).")
    if total["n"] >= 6 and (total["sobreestimados"] > 0.8 * total["n"] or total["subestimados"] > 0.8 * total["n"]):
        avisos.append("Más del 80 % de los residuales tiene el mismo signo.")
    if total["n"] < 10:
        avisos.append("Menos de 10 puntos: los estadísticos son poco representativos.")
    for g, e in por_grupo.items():
        if not math.isnan(e["rmse_normalizado_pct"]) and e["rmse"] > 1.5 * total["rmse"]:
            avisos.append(f"El grupo «{g}» calibra peor que el conjunto (RMSE {fmt(e['rmse'])} {a.unidad}).")

    if a.json:
        print(json.dumps({"total": total, "por_grupo": por_grupo,
                          "mayores_residuales": [{k: d[k] for k in ("punto", "grupo", "obs", "sim", "res")} for d in peores],
                          "avisos": avisos}, ensure_ascii=False, indent=2))
        return 0

    u = a.unidad
    print(f"# Calibración: {a.csv}\n")
    print(f"| Conjunto | n | Error medio ({u}) | Error medio absoluto ({u}) | RMSE ({u}) | RMSE normalizado (%) | R² | Residual mín/máx ({u}) |")
    print("|---|---|---|---|---|---|---|---|")

    def fila(nombre, e):
        print(f"| {nombre} | {e['n']} | {fmt(e['error_medio'])} | {fmt(e['error_medio_absoluto'])} | {fmt(e['rmse'])} | "
              f"{fmt(e['rmse_normalizado_pct'])} | {fmt(e['r2'], 4)} | {fmt(e['residual_minimo'])} / {fmt(e['residual_maximo'])} |")

    fila("Total", total)
    for g, e in por_grupo.items():
        fila(g, e)
    print(f"\n## Mayores residuales\n\n| Punto | Grupo | Observado ({u}) | Simulado ({u}) | Residual ({u}) |\n|---|---|---|---|---|")
    for d in peores:
        print(f"| {d['punto']} | {d['grupo'] or '—'} | {fmt(d['obs'], 6)} | {fmt(d['sim'], 6)} | {d['res']:+.3g} |")
    print("\n## Lectura\n")
    for av in avisos:
        print("- " + av)
    print(f"\nResidual = simulado − observado. RMSE normalizado = RMSE / (máximo − mínimo observado). "
          f"La referencia de {a.umbral:g} % es una convención de uso común: usa el criterio que exija la guía o el cliente del proyecto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
