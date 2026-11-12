#!/usr/bin/env python3
"""Balance ácido-base de ensayos estáticos y clasificación de materiales.

Entrada: CSV con una fila por muestra:
  muestra, grupo, S_sulfuro, S_total, PN, pH_pasta, pH_NAG
  - S_sulfuro y S_total en % en peso. Si falta S_sulfuro se usa S_total (conservador).
  - PN: potencial de neutralización en kg CaCO3/t.
  - grupo (unidad geoambiental), pH_pasta y pH_NAG son opcionales.
Acepta separador coma o punto y coma, y coma decimal. Solo biblioteca estándar.

Cálculo: PA = 31,25 x S(%), PNN = PN - PA, razón = PN / PA.

Ejemplos:
  python aba.py ensayos.csv
  python aba.py ensayos.csv --razon-generador 1 --razon-no-generador 3 --json
"""
import argparse
import csv
import json
import math
import sys

FACTOR_PA = 31.25  # kg CaCO3/t por cada 1 % de azufre como sulfuro
ALIAS = {
    "muestra": ("muestra", "id", "codigo", "código", "sample"),
    "grupo": ("grupo", "unidad", "litologia", "litología", "ugam", "tipo"),
    "s_sulfuro": ("s_sulfuro", "s sulfuro", "azufre_sulfuro", "s2", "s_sulfide", "ssulfuro"),
    "s_total": ("s_total", "s total", "azufre_total", "s", "stotal"),
    "pn": ("pn", "np", "potencial_neutralizacion", "potencial_neutralización"),
    "ph_pasta": ("ph_pasta", "ph pasta", "paste_ph", "phpasta"),
    "ph_nag": ("ph_nag", "nag_ph", "ph nag", "nagph", "phnag"),
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
    if not v or v.startswith("<"):
        return None
    if delim != ",":
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def columnas(filas):
    m = {}
    for col in filas[0].keys():
        if not col:
            continue
        clave = col.strip().lower().split("(")[0].strip().replace("%", "").strip()
        for canon, alias in ALIAS.items():
            if clave in alias and canon not in m:
                m[canon] = col
    return m


def clasificar(pa, pn, razon_gen=1.0, razon_no=2.0, pnn_limite=20.0):
    """Devuelve PNN, razón PN/PA y la clase por cada criterio y combinada."""
    pnn = pn - pa
    razon = pn / pa if pa > 0 else float("inf")
    por_razon = "generador" if razon < razon_gen else ("no generador" if razon > razon_no else "incierto")
    por_pnn = "generador" if pnn < -pnn_limite else ("no generador" if pnn > pnn_limite else "incierto")
    clase = por_razon if por_razon == por_pnn else "incierto"
    return {"PNN": pnn, "razon": razon, "por_razon": por_razon, "por_pnn": por_pnn, "clase": clase}


def fmt(v, c=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if math.isinf(v):
        return "sin PA"
    if abs(v) >= 100:
        return f"{v:.0f}"
    return f"{v:.{c}g}"


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Balance ácido-base y clasificación de materiales.")
    p.add_argument("csv", help="CSV con muestra, S_sulfuro o S_total (%%), PN (kg CaCO3/t)")
    p.add_argument("--razon-generador", type=float, default=1.0, help="PN/PA bajo el cual el material es generador (por defecto 1)")
    p.add_argument("--razon-no-generador", type=float, default=2.0, help="PN/PA sobre el cual no es generador (por defecto 2)")
    p.add_argument("--pnn-limite", type=float, default=20.0, help="Banda de incertidumbre del PNN en kg CaCO3/t (por defecto ±20)")
    p.add_argument("--ph-nag", type=float, default=4.5, help="pH de generación neta de ácido bajo el cual se considera que genera (por defecto 4,5)")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    if not filas:
        raise SystemExit("El archivo no tiene muestras.")
    c = columnas(filas)
    if "pn" not in c or ("s_sulfuro" not in c and "s_total" not in c):
        raise SystemExit("Faltan columnas. Se esperan: muestra, S_sulfuro o S_total (% en peso) y PN (kg CaCO3/t).")

    res = []
    for i, f in enumerate(filas):
        ss = numero(f[c["s_sulfuro"]], delim) if "s_sulfuro" in c else None
        st = numero(f[c["s_total"]], delim) if "s_total" in c else None
        pn = numero(f[c["pn"]], delim)
        nombre = (f[c["muestra"]].strip() if "muestra" in c else "") or f"fila {i + 2}"
        grupo = f[c["grupo"]].strip() if "grupo" in c else ""
        if pn is None or (ss is None and st is None):
            res.append({"muestra": nombre, "grupo": grupo, "clase": "sin datos", "avisos": ["falta azufre o PN"]})
            continue
        avisos = []
        s = ss
        if s is None:
            s = st
            avisos.append("PA calculado con azufre total (conservador): falta el azufre como sulfuro")
        elif st is not None and ss > st * 1.05:
            avisos.append("el azufre como sulfuro supera al azufre total: revisa el certificado")
        pa = FACTOR_PA * s
        k = clasificar(pa, pn, a.razon_generador, a.razon_no_generador, a.pnn_limite)
        r = {"muestra": nombre, "grupo": grupo, "S_usado_pct": s, "PA": pa, "PN": pn, **k}
        if k["por_razon"] != k["por_pnn"]:
            avisos.append(f"los criterios no coinciden (razón: {k['por_razon']}; PNN: {k['por_pnn']})")
        if s < 0.1:
            avisos.append("azufre bajo (menos de 0,1 %): la razón PN/PA es muy sensible al error analítico")
        if "ph_pasta" in c:
            ph = numero(f[c["ph_pasta"]], delim)
            if ph is not None:
                r["pH_pasta"] = ph
                if ph < 5.0:
                    avisos.append(f"pH en pasta {ph:g}: el material ya presenta acidez")
        if "ph_nag" in c:
            nag = numero(f[c["ph_nag"]], delim)
            if nag is not None:
                r["pH_NAG"] = nag
                r["NAG"] = "genera" if nag < a.ph_nag else "no genera"
                if r["NAG"] == "genera" and k["clase"] == "no generador":
                    avisos.append("el pH de generación neta indica que genera, contra el balance ácido-base: pide ensayo cinético")
                if r["NAG"] == "no genera" and k["clase"] == "generador":
                    avisos.append("el pH de generación neta indica que no genera, contra el balance ácido-base: revisa mineralogía")
        r["avisos"] = avisos
        res.append(r)

    validas = [r for r in res if r["clase"] != "sin datos"]
    clases = ("generador", "incierto", "no generador")
    total = {k: sum(1 for r in validas if r["clase"] == k) for k in clases}
    grupos = {}
    for r in validas:
        if r["grupo"]:
            g = grupos.setdefault(r["grupo"], {k: 0 for k in clases})
            g[r["clase"]] += 1
    cineticos = [r["muestra"] for r in validas if r["clase"] == "incierto" or any("generación neta" in av for av in r["avisos"])]
    criterios = {"razon_generador": a.razon_generador, "razon_no_generador": a.razon_no_generador,
                 "pnn_limite": a.pnn_limite, "ph_nag": a.ph_nag, "factor_pa": FACTOR_PA}

    if a.json:
        print(json.dumps({"criterios": criterios, "muestras": res, "resumen": total, "por_grupo": grupos, "requieren_cinetico": cineticos},
                         ensure_ascii=False, indent=2).replace("Infinity", "null"))
        return 0

    print(f"# Balance ácido-base: {a.csv}\n")
    print("| Muestra | Grupo | S (%) | PA | PN | PNN | PN/PA | pH pasta | pH NAG | Clase |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in res:
        if r["clase"] == "sin datos":
            print(f"| {r['muestra']} | {r['grupo'] or '—'} | — | — | — | — | — | — | — | sin datos |")
            continue
        print(f"| {r['muestra']} | {r['grupo'] or '—'} | {fmt(r['S_usado_pct'])} | {fmt(r['PA'])} | {fmt(r['PN'])} | "
              f"{r['PNN']:+.3g} | {fmt(r['razon'])} | {fmt(r.get('pH_pasta'))} | {fmt(r.get('pH_NAG'))} | {r['clase']} |")
    n = len(validas)
    if n:
        print("\nResumen: " + ", ".join(f"{total[k]} {k} ({100 * total[k] / n:.0f} %)" for k in clases) + f", de {n} muestras.")
    if grupos:
        print("\n## Por grupo\n\n| Grupo | Muestras | Generador | Incierto | No generador |\n|---|---|---|---|---|")
        for g, t in sorted(grupos.items()):
            m = sum(t.values())
            print(f"| {g} | {m} | {t['generador']} | {t['incierto']} | {t['no generador']} |")
            if m < 3:
                print(f"| | | | | *menos de 3 muestras: clasificación preliminar* |")
    if cineticos:
        print("\nMuestras que piden mineralogía o ensayo cinético antes de concluir (inciertas o con criterios contradictorios): "
              + ", ".join(cineticos) + ".")
    notas = [r for r in res if r.get("avisos")]
    if notas:
        print("\n## Observaciones\n")
        for r in notas:
            print(f"- **{r['muestra']}**: " + "; ".join(r["avisos"]) + ".")
    print(f"\nPA = 31,25 × S (%), PNN = PN − PA, en kg CaCO₃/t. Criterio usado: generador si PN/PA < {a.razon_generador:g} y "
          f"PNN < −{a.pnn_limite:g}; no generador si PN/PA > {a.razon_no_generador:g} y PNN > +{a.pnn_limite:g}; el resto, incierto. "
          "Son criterios de uso común: aplica los que exija la guía del proyecto y cita su fuente. El resumen por grupo cuenta muestras; "
          "no clasifica la unidad completa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
