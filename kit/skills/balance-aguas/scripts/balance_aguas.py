#!/usr/bin/env python3
"""Cierre del balance de aguas de una cuenca o de un componente minero.

Entrada: CSV con una fila por término del balance:
  periodo, componente, tipo, valor
  - tipo: entrada, salida o almacenamiento (variación de almacenamiento; positiva si aumenta).
  - periodo es opcional (mes, año, escenario). Todos los valores en la misma unidad.
Acepta separador coma o punto y coma, y coma decimal. Solo biblioteca estándar.

Cierre = entradas − salidas − variación de almacenamiento.
Error (%) = 100 × cierre / mayor(entradas, salidas).

Ejemplos:
  python balance_aguas.py balance.csv --unidad "m3/mes"
  python balance_aguas.py balance.csv --tolerancia 10 --json
"""
import argparse
import csv
import json
import sys

ALIAS = {
    "periodo": ("periodo", "período", "mes", "año", "ano", "escenario", "fecha"),
    "componente": ("componente", "termino", "término", "flujo", "item", "ítem", "descripcion", "descripción"),
    "tipo": ("tipo", "clase", "sentido"),
    "valor": ("valor", "caudal", "volumen", "q"),
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


def tipo_de(texto):
    t = (texto or "").strip().lower()
    if t.startswith(("ent", "apo", "in", "+")):
        return "entrada"
    if t.startswith(("sal", "out", "per", "-")):
        return "salida"
    if t.startswith(("alm", "var", "del", "δ", "stor")):
        return "almacenamiento"
    return None


def cerrar(terminos, tolerancia):
    """terminos: lista de (tipo, valor). Devuelve sumas, cierre, error y estado."""
    e = sum(v for t, v in terminos if t == "entrada")
    s = sum(v for t, v in terminos if t == "salida")
    d = sum(v for t, v in terminos if t == "almacenamiento")
    cierre = e - s - d
    base = max(abs(e), abs(s))
    error = 100.0 * cierre / base if base > 0 else float("nan")
    if error != error:
        estado = "sin datos"
    elif abs(error) <= tolerancia:
        estado = "cierra"
    elif abs(error) <= 2 * tolerancia:
        estado = "revisar"
    else:
        estado = "no cierra"
    return {"entradas": e, "salidas": s, "almacenamiento": d, "cierre": cierre, "error_pct": error, "estado": estado}


def fmt(v):
    if v is None or v != v:
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:.4g}"


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Cierre del balance de aguas por período.")
    p.add_argument("csv", help="CSV con periodo, componente, tipo, valor")
    p.add_argument("--tolerancia", type=float, default=5.0, help="Error de cierre aceptable en %% (por defecto 5)")
    p.add_argument("--unidad", default="", help="Unidad de los valores, para los encabezados (por ejemplo L/s o m3/mes)")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    if not filas:
        raise SystemExit("El archivo no tiene datos.")
    c = {k: columna(filas, v) for k, v in ALIAS.items()}
    if not c["tipo"] or not c["valor"]:
        raise SystemExit("No encuentro las columnas. Se esperan: periodo (opcional), componente, tipo, valor.")
    periodos, orden, sin_tipo = {}, [], []
    for i, f in enumerate(filas):
        t = tipo_de(f[c["tipo"]])
        v = numero(f[c["valor"]], delim)
        nombre = (f[c["componente"]].strip() if c["componente"] else "") or f"fila {i + 2}"
        if t is None or v is None:
            sin_tipo.append(nombre)
            continue
        per = (f[c["periodo"]].strip() if c["periodo"] else "") or "total"
        if per not in periodos:
            periodos[per] = []
            orden.append(per)
        periodos[per].append((t, v, nombre))
    if not periodos:
        raise SystemExit("Ninguna fila tiene tipo (entrada, salida, almacenamiento) y valor numérico.")

    res = {per: cerrar([(t, v) for t, v, _ in periodos[per]], a.tolerancia) for per in orden}
    todo = [(t, v) for per in orden for t, v, _ in periodos[per]]
    total = cerrar(todo, a.tolerancia)
    aporte = {}
    for per in orden:
        for t, v, nombre in periodos[per]:
            aporte.setdefault((t, nombre), 0.0)
            aporte[(t, nombre)] += v
    desglose = []
    for (t, nombre), v in aporte.items():
        ref = total["entradas"] if t == "entrada" else total["salidas"] if t == "salida" else None
        desglose.append({"tipo": t, "componente": nombre, "valor": v, "porcentaje": 100.0 * v / ref if ref else None})
    desglose.sort(key=lambda d: (("entrada", "salida", "almacenamiento").index(d["tipo"]), -abs(d["valor"])))

    avisos = []
    for per in orden:
        r = res[per]
        if r["estado"] == "no cierra":
            signo = "sobran entradas o faltan salidas" if r["cierre"] > 0 else "sobran salidas o faltan entradas"
            avisos.append(f"{per}: no cierra ({r['error_pct']:+.1f} %); {signo}.")
        elif r["estado"] == "revisar":
            avisos.append(f"{per}: error de {r['error_pct']:+.1f} %, sobre la tolerancia de {a.tolerancia:g} %.")
    if len(orden) > 1:
        signos = [res[per]["cierre"] > 0 for per in orden if res[per]["cierre"] != 0]
        if len(signos) >= 3 and (all(signos) or not any(signos)):
            avisos.append("El error tiene el mismo signo en todos los períodos: apunta a un término mal estimado o ausente, no a ruido.")
    if not any(t == "almacenamiento" for t, _ in todo):
        avisos.append("No hay término de almacenamiento: el balance supone régimen permanente.")
    if sin_tipo:
        avisos.append("Filas sin tipo o sin valor, no consideradas: " + ", ".join(sin_tipo[:8]) + ("…" if len(sin_tipo) > 8 else "") + ".")

    if a.json:
        print(json.dumps({"tolerancia_pct": a.tolerancia, "unidad": a.unidad, "periodos": res, "total": total,
                          "desglose": desglose, "avisos": avisos}, ensure_ascii=False, indent=2).replace("NaN", "null"))
        return 0

    u = f" ({a.unidad})" if a.unidad else ""
    print(f"# Balance de aguas: {a.csv}\n")
    print(f"| Período | Entradas{u} | Salidas{u} | Δ almacenamiento{u} | Cierre{u} | Error (%) | Estado |")
    print("|---|---|---|---|---|---|---|")
    for per in orden:
        r = res[per]
        print(f"| {per} | {fmt(r['entradas'])} | {fmt(r['salidas'])} | {fmt(r['almacenamiento'])} | {fmt(r['cierre'])} | "
              f"{r['error_pct']:+.1f} | {r['estado']} |")
    if len(orden) > 1:
        print(f"| **Suma** | {fmt(total['entradas'])} | {fmt(total['salidas'])} | {fmt(total['almacenamiento'])} | "
              f"{fmt(total['cierre'])} | {total['error_pct']:+.1f} | {total['estado']} |")
    print(f"\n## Peso de cada término\n\n| Tipo | Componente | Valor{u} | % de su grupo |\n|---|---|---|---|")
    for d in desglose:
        pct = "—" if d["porcentaje"] is None else f"{d['porcentaje']:.0f}"
        print(f"| {d['tipo']} | {d['componente']} | {fmt(d['valor'])} | {pct} |")
    if avisos:
        print("\n## Lectura\n")
        for av in avisos:
            print("- " + av)
    print(f"\nCierre = entradas − salidas − variación de almacenamiento. Error = 100 × cierre / mayor(entradas, salidas). "
          f"Tolerancia usada: ±{a.tolerancia:g} %. Un error alto se investiga; no se reparte entre términos para que cuadre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
