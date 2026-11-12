#!/usr/bin/env python3
"""Compara series de monitoreo con los umbrales de un plan de alerta temprana.

Entradas:
  series.csv    fecha, punto, valor
  umbrales.csv  punto, alerta, accion, sentido
     sentido = bajo   el estado se activa cuando el valor es menor o igual al umbral (cotas de nivel, caudales)
     sentido = sobre  se activa cuando el valor es mayor o igual al umbral (concentraciones, profundidad de nivel)
     Si falta, se asume «bajo». «accion» y «unidad» son opcionales.
     Una medición igual al umbral cuenta como superación, salvo con --estricto.

Fechas AAAA-MM-DD, DD-MM-AAAA o DD/MM/AAAA. Acepta separador coma o punto y coma, y coma decimal.
Solo biblioteca estándar.

Ejemplos:
  python umbrales.py series.csv umbrales.csv
  python umbrales.py series.csv umbrales.csv --consecutivas 3 --json
"""
import argparse
import csv
import datetime as dt
import json
import sys


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


def nivel_de(valor, alerta, accion, sentido, estricto=False):
    """0 normal, 1 alerta, 2 acción. Con estricto, una medición igual al umbral no cuenta."""
    def pasa(umbral):
        if umbral is None:
            return False
        if sentido == "sobre":
            return valor > umbral if estricto else valor >= umbral
        return valor < umbral if estricto else valor <= umbral
    if pasa(accion):
        return 2
    return 1 if pasa(alerta) else 0


def evaluar(serie, alerta, accion, sentido, consecutivas=1, estricto=False):
    """serie: lista ordenada de (fecha, valor)."""
    niveles = [nivel_de(v, alerta, accion, sentido, estricto) for _, v in serie]
    racha_alerta = racha_accion = 0
    for n in reversed(niveles):
        if n >= 1:
            racha_alerta += 1
        else:
            break
    for n in reversed(niveles):
        if n >= 2:
            racha_accion += 1
        else:
            break
    if racha_accion >= consecutivas:
        estado = "acción"
    elif racha_alerta >= consecutivas:
        estado = "alerta"
    elif niveles[-1] >= 1:
        estado = "en observación"
    else:
        estado = "normal"
    ult_f, ult_v = serie[-1]
    margen = None
    if alerta is not None:
        margen = (alerta - ult_v) if sentido == "sobre" else (ult_v - alerta)
    primera = next((f for (f, _), n in zip(serie, niveles) if n >= 1), None)
    return {
        "estado": estado, "ultimo_valor": ult_v, "ultima_fecha": ult_f.isoformat(), "mediciones": len(serie),
        "en_alerta_o_mas": sum(1 for n in niveles if n >= 1), "en_accion": sum(1 for n in niveles if n >= 2),
        "racha_alerta": racha_alerta, "racha_accion": racha_accion, "margen_a_alerta": margen,
        "primera_superacion": primera.isoformat() if primera else None,
    }


def fmt(v):
    if v is None:
        return "—"
    return f"{v:.2f}" if abs(v) >= 100 else f"{v:.4g}"


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Estado de cada punto de control frente a sus umbrales de alerta y de acción.")
    p.add_argument("series", help="CSV con fecha, punto, valor")
    p.add_argument("umbrales", help="CSV con punto, alerta, accion, sentido")
    p.add_argument("--consecutivas", type=int, default=1, help="Mediciones seguidas que activan un estado (por defecto 1)")
    p.add_argument("--estricto", action="store_true", help="Una medición igual al umbral no cuenta como superación")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)
    if a.consecutivas < 1:
        raise SystemExit("--consecutivas debe ser 1 o más.")

    fu, du = leer_csv(a.umbrales)
    cu = {k: columna(fu, v) for k, v in {"punto": ("punto", "pozo", "id", "codigo", "código"),
                                         "alerta": ("alerta", "umbral_alerta", "umbral", "nivel_alerta"),
                                         "accion": ("accion", "acción", "umbral_accion", "umbral_acción", "nivel_accion"),
                                         "sentido": ("sentido", "tipo", "direccion", "dirección"),
                                         "unidad": ("unidad", "unidades", "variable")}.items()}
    if not cu["punto"] or not cu["alerta"]:
        raise SystemExit("El archivo de umbrales debe traer las columnas punto y alerta (y, si existe, accion y sentido).")
    umbrales = {}
    for f in fu:
        pt = f[cu["punto"]].strip()
        s = (f[cu["sentido"]].strip().lower() if cu["sentido"] else "") or "bajo"
        s = "sobre" if s.startswith(("sob", "may", "sup", "max", "máx")) else "bajo"
        umbrales[pt] = {"alerta": numero(f[cu["alerta"]], du),
                        "accion": numero(f[cu["accion"]], du) if cu["accion"] else None, "sentido": s,
                        "unidad": (f[cu["unidad"]].strip() if cu["unidad"] else "")}

    fs, ds = leer_csv(a.series)
    cs = {k: columna(fs, v) for k, v in {"fecha": ("fecha", "date", "fecha_medicion", "fecha_muestreo"),
                                         "punto": ("punto", "pozo", "id", "codigo", "código", "estacion", "estación"),
                                         "valor": ("valor", "nivel", "nivel_m", "cota", "cota_msnm", "concentracion", "concentración")}.items()}
    if not cs["fecha"] or not cs["punto"] or not cs["valor"]:
        raise SystemExit("El archivo de series debe traer las columnas fecha, punto y valor.")
    series, descartadas = {}, 0
    for f in fs:
        d, v = fecha(f[cs["fecha"]]), numero(f[cs["valor"]], ds)
        if d is None or v is None:
            descartadas += 1
            continue
        series.setdefault(f[cs["punto"]].strip(), []).append((d, v))

    res = []
    for pt in sorted(set(series) | set(umbrales)):
        u = umbrales.get(pt)
        s = sorted(series.get(pt, []))
        if not s:
            res.append({"punto": pt, "estado": "sin datos", "alerta": u["alerta"], "accion": u["accion"], "sentido": u["sentido"], "unidad": u["unidad"]})
            continue
        if not u or u["alerta"] is None:
            res.append({"punto": pt, "estado": "sin umbral", "ultimo_valor": s[-1][1], "ultima_fecha": s[-1][0].isoformat(),
                        "mediciones": len(s), "alerta": None, "accion": None, "sentido": None, "unidad": u["unidad"] if u else ""})
            continue
        avisos = []
        if u["accion"] is not None:
            mal = u["accion"] > u["alerta"] if u["sentido"] == "bajo" else u["accion"] < u["alerta"]
            if mal:
                avisos.append("el umbral de acción queda antes que el de alerta: revisa el archivo de umbrales")
        r = {"punto": pt, "alerta": u["alerta"], "accion": u["accion"], "sentido": u["sentido"], "unidad": u["unidad"],
             **evaluar(s, u["alerta"], u["accion"], u["sentido"], a.consecutivas, a.estricto), "avisos": avisos}
        if any(v == u["alerta"] or v == u["accion"] for _, v in s):
            avisos.append("hay mediciones iguales al umbral: " + ("no cuentan como superación (modo estricto)" if a.estricto
                                                                   else "cuentan como superación; si el plan dice lo contrario, usa --estricto"))
        res.append(r)

    orden = {"acción": 0, "alerta": 1, "en observación": 2, "normal": 3, "sin umbral": 4, "sin datos": 5}
    res.sort(key=lambda r: (orden[r["estado"]], r["punto"]))
    cuenta = {}
    for r in res:
        cuenta[r["estado"]] = cuenta.get(r["estado"], 0) + 1

    if a.json:
        print(json.dumps({"consecutivas": a.consecutivas, "estricto": a.estricto, "resumen": cuenta, "puntos": res, "filas_descartadas": descartadas},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"# Estado frente a umbrales: {a.series}\n")
    print("| Punto | Estado | Último valor | Unidad | Fecha | Umbral de alerta | Umbral de acción | Margen a la alerta | Seguidas en alerta | Seguidas en acción | Primera superación |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res:
        un = r.get("unidad") or "—"
        if r["estado"] == "sin datos":
            print(f"| {r['punto']} | sin datos | — | {un} | — | {fmt(r['alerta'])} | {fmt(r['accion'])} | — | — | — | — |")
            continue
        if r["estado"] == "sin umbral":
            print(f"| {r['punto']} | sin umbral | {fmt(r['ultimo_valor'])} | {un} | {r['ultima_fecha']} | — | — | — | — | — | — |")
            continue
        if r["sentido"] == "sobre":
            sim = ">" if a.estricto else "≥"
        else:
            sim = "<" if a.estricto else "≤"
        print(f"| {r['punto']} | **{r['estado']}** | {fmt(r['ultimo_valor'])} | {un} | {r['ultima_fecha']} | {sim} {fmt(r['alerta'])} | "
              f"{(sim + ' ' + fmt(r['accion'])) if r['accion'] is not None else '—'} | {r['margen_a_alerta']:+.3g} | "
              f"{r['racha_alerta']} | {r['racha_accion'] if r['accion'] is not None else '—'} | {r['primera_superacion'] or '—'} |")
    print("\nResumen: " + ", ".join(f"{v} en {k}" if k in ("acción", "alerta", "observación") else f"{v} {k}" for k, v in cuenta.items()) + ".")
    notas = []
    for r in res:
        for av in r.get("avisos", []):
            notas.append(f"- **{r['punto']}**: {av}.")
        if r["estado"] == "en observación":
            notas.append(f"- **{r['punto']}**: la última medición supera el umbral, pero aún no suma {a.consecutivas} seguidas.")
        if r["estado"] == "normal" and r.get("margen_a_alerta") is not None and r["en_alerta_o_mas"]:
            notas.append(f"- **{r['punto']}**: hoy está normal, pero superó el umbral {r['en_alerta_o_mas']} veces en la serie.")
    if notas:
        print("\n## Observaciones\n")
        print("\n".join(notas))
    if descartadas:
        print(f"\nSe descartaron {descartadas} filas sin fecha o sin valor numérico.")
    igual = "más allá del umbral (una medición igual al umbral no cuenta)" if a.estricto else "en o más allá del umbral (una medición igual al umbral cuenta)"
    print(f"\nUn estado se activa con {a.consecutivas} medición(es) seguida(s) {igual}. El margen es la distancia que queda "
          "hasta el umbral de alerta (negativo si ya se superó). Los umbrales se toman del plan aprobado: este script no los propone ni los ajusta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
