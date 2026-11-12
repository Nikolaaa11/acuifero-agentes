#!/usr/bin/env python3
"""Control de calidad hidroquímico: balance iónico, facies y diagrama de Piper.

Entrada: CSV con una fila por muestra. Columnas en mg/L:
  muestra, Ca, Mg, Na, K, HCO3, CO3, Cl, SO4, NO3
Opcionales: CE (µS/cm), SDT (mg/L), pH.
Acepta separador coma o punto y coma, y coma decimal. Los valores «<0,01»
se toman como cero para el balance y se cuentan como bajo el límite.

Ejemplos:
  python balance_ionico.py muestras.csv
  python balance_ionico.py muestras.csv --piper piper.svg --json
"""
import argparse
import csv
import json
import math
import sys

# Peso equivalente (g/eq) = masa molar / carga
PESO_EQ = {
    "Ca": 20.039, "Mg": 12.1525, "Na": 22.9898, "K": 39.0983,
    "HCO3": 61.0168, "CO3": 30.0044, "Cl": 35.453, "SO4": 48.0313, "NO3": 62.0049,
}
CATIONES = ("Ca", "Mg", "Na", "K")
ANIONES = ("HCO3", "CO3", "Cl", "SO4", "NO3")
ALIAS = {
    "muestra": ("muestra", "id", "punto", "pozo", "codigo", "código", "sample"),
    "CE": ("ce", "conductividad", "ce_us_cm", "ec"),
    "SDT": ("sdt", "tds", "std", "solidos_disueltos", "sólidos_disueltos"),
    "pH": ("ph",),
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
    """Devuelve (valor, bajo_limite)."""
    v = (v or "").strip()
    if not v or v.lower() in ("nd", "n.d.", "-", "na", "n/a"):
        return None, False
    bajo = v.startswith("<")
    if bajo:
        v = v[1:].strip()
    if delim != ",":
        v = v.replace(",", ".")
    try:
        x = float(v)
    except ValueError:
        return None, False
    return (0.0, True) if bajo else (x, False)


def mapa_columnas(filas):
    """Relaciona el nombre canónico con la columna real (sin mayúsculas ni unidades)."""
    m = {}
    for col in filas[0].keys():
        if not col:
            continue
        base = col.strip().split("(")[0].split("[")[0].strip()
        clave = base.lower().replace("_mg_l", "").replace(" mg/l", "").replace("-", "").replace("+", "").strip()
        for ion in PESO_EQ:
            if clave == ion.lower():
                m[ion] = col
        for canon, alias in ALIAS.items():
            if clave in alias:
                m[canon] = col
    return m


def facies(pc, pa):
    """pc y pa: porcentajes en meq. Devuelve el tipo de agua."""
    cat = {"cálcica": pc["Ca"], "magnésica": pc["Mg"], "sódica": pc["Na"] + pc["K"]}
    an = {"bicarbonatada": pa["HCO3"] + pa["CO3"], "clorurada": pa["Cl"], "sulfatada": pa["SO4"]}

    def dominante(d):
        orden = sorted(d.items(), key=lambda kv: kv[1], reverse=True)
        if orden[0][1] >= 50:
            return orden[0][0]
        return orden[0][0] + "-" + orden[1][0]

    return (dominante(an) + " " + dominante(cat)).capitalize()


def analizar(fila, cols, delim, limite):
    meq = {}
    bajo_limite = []
    faltan = []
    for ion in PESO_EQ:
        if ion not in cols:
            meq[ion] = 0.0
            if ion not in ("CO3", "NO3", "K"):
                faltan.append(ion)
            continue
        x, bajo = numero(fila[cols[ion]], delim)
        if x is None:
            meq[ion] = 0.0
            if ion not in ("CO3", "NO3"):
                faltan.append(ion)
            continue
        if bajo:
            bajo_limite.append(ion)
        meq[ion] = x / PESO_EQ[ion]
    sc = sum(meq[i] for i in CATIONES)
    sa = sum(meq[i] for i in ANIONES)
    r = {"muestra": (fila.get(cols.get("muestra", ""), "") or "").strip() or "s/n",
         "suma_cationes_meq": sc, "suma_aniones_meq": sa, "faltan": faltan, "bajo_limite": bajo_limite}
    if sc + sa == 0:
        r.update({"error_pct": None, "estado": "sin datos", "tipo": "—"})
        return r
    err = 100.0 * (sc - sa) / (sc + sa)
    r["error_pct"] = err
    if faltan:
        r["estado"] = "incompleta"
    elif abs(err) <= limite:
        r["estado"] = "aceptada"
    elif abs(err) <= 2 * limite:
        r["estado"] = "dudosa"
    else:
        r["estado"] = "rechazada"
    pc = {i: 100.0 * meq[i] / sc if sc else 0.0 for i in CATIONES}
    base_an = meq["HCO3"] + meq["CO3"] + meq["Cl"] + meq["SO4"]
    pa = {i: 100.0 * meq[i] / base_an if base_an else 0.0 for i in ("HCO3", "CO3", "Cl", "SO4")}
    r["pct_cationes"] = pc
    r["pct_aniones"] = pa
    r["tipo"] = facies(pc, pa) if sc and base_an else "—"
    r["meq"] = meq

    # Chequeos adicionales
    mgl = {}
    for ion in PESO_EQ:
        mgl[ion] = meq[ion] * PESO_EQ[ion]
    sdt_calc = sum(mgl[i] for i in PESO_EQ if i != "HCO3") + 0.4917 * mgl["HCO3"]
    r["sdt_calculado_mg_l"] = sdt_calc
    if "SDT" in cols:
        sdt, _ = numero(fila[cols["SDT"]], delim)
        if sdt and sdt_calc:
            r["sdt_medido_mg_l"] = sdt
            r["razon_sdt"] = sdt / sdt_calc
    if "CE" in cols:
        ce, _ = numero(fila[cols["CE"]], delim)
        if ce:
            r["ce_us_cm"] = ce
            r["razon_ce_cationes"] = (sc * 100.0) / ce
            r["razon_ce_aniones"] = (sa * 100.0) / ce
            if sdt_calc:
                r["razon_sdt_ce"] = sdt_calc / ce
    if "pH" in cols:
        ph, _ = numero(fila[cols["pH"]], delim)
        if ph:
            r["pH"] = ph
    avisos = []
    if r.get("razon_sdt") is not None and not (1.0 <= r["razon_sdt"] <= 1.2):
        avisos.append(f"SDT medido/calculado = {r['razon_sdt']:.2f} (se espera entre 1,0 y 1,2)")
    for nombre in ("razon_ce_cationes", "razon_ce_aniones"):
        v = r.get(nombre)
        if v is not None and not (0.9 <= v <= 1.1):
            quien = "cationes" if "cationes" in nombre else "aniones"
            avisos.append(f"100·Σ{quien}/CE = {v:.2f} (se espera entre 0,9 y 1,1)")
    if r.get("razon_sdt_ce") is not None and not (0.55 <= r["razon_sdt_ce"] <= 0.75):
        avisos.append(f"SDT calculado/CE = {r['razon_sdt_ce']:.2f} (habitual entre 0,55 y 0,75; aguas sulfatadas pueden superar ese rango)")
    if err > limite:
        avisos.append("Sobran cationes: revisa alcalinidad no informada, aniones faltantes o sodio sobreestimado")
    elif err < -limite:
        avisos.append("Sobran aniones: revisa cationes no analizados (Fe, Al, NH4 en aguas ácidas) o dilución")
    r["avisos"] = avisos
    return r


def piper_svg(resultados, ruta):
    """Dibuja un diagrama de Piper en SVG, sin dependencias."""
    L = 260.0
    h = L * math.sqrt(3) / 2
    sep = 60.0
    ox, oy = 50.0, 60.0 + 2 * h + sep * math.sqrt(3) / 2
    ancho = 2 * L + sep + 100
    alto = oy + 70
    r3 = math.sqrt(3)

    def P(x, y):
        return ox + x, oy - y

    def cat_xy(ca, mg, nak):
        t = ca + mg + nak
        return (nak + 0.5 * mg) / t * L, mg / t * h

    def an_xy(hco3, so4, cl):
        t = hco3 + so4 + cl
        return L + sep + (cl + 0.5 * so4) / t * L, so4 / t * h

    def rombo(c, a):
        x = (a[1] - c[1] + r3 * (c[0] + a[0])) / (2 * r3)
        y = c[1] + r3 * (x - c[0])
        return x, y

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho:.0f} {alto:.0f}" '
           f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="11">',
           f'<rect width="{ancho:.0f}" height="{alto:.0f}" fill="#fff"/>']

    def poli(pts, **kw):
        attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        d = " ".join(f"{P(*p)[0]:.1f},{P(*p)[1]:.1f}" for p in pts)
        out.append(f'<polygon points="{d}" {attrs}/>')

    def linea(a, b, color="#d2d2d7", w=0.6):
        (x1, y1), (x2, y2) = P(*a), P(*b)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{w}"/>')

    def texto(p, s, ancla="middle", dy=0, peso="400", color="#1d1d1f"):
        x, y = P(*p)
        out.append(f'<text x="{x:.1f}" y="{y + dy:.1f}" text-anchor="{ancla}" font-weight="{peso}" fill="{color}">{s}</text>')

    # Triángulos y grilla
    for x0 in (0.0, L + sep):
        A, B, C = (x0, 0), (x0 + L, 0), (x0 + L / 2, h)
        for k in range(1, 5):
            f = k / 5
            linea((x0 + f * L, 0), (x0 + f * L + (1 - f) * L / 2, (1 - f) * h))
            linea((x0 + f * L, 0), (x0 + f * L / 2, f * h))
            linea((x0 + f * L / 2, f * h), (x0 + L - f * L / 2, f * h))
        poli([A, B, C], fill="none", stroke="#1d1d1f", stroke_width="1")
    # Rombo
    c_izq, c_der = (L / 2, h), (L + sep + L / 2, h)
    abajo = rombo(cat_xy(0, 0, 1), an_xy(1, 0, 0))
    arriba = rombo(cat_xy(1, 0, 0), an_xy(0, 0, 1))
    izq = rombo(cat_xy(1, 0, 0), an_xy(1, 0, 0))
    der = rombo(cat_xy(0, 0, 1), an_xy(0, 0, 1))
    del c_izq, c_der
    for k in range(1, 5):
        f = k / 5
        linea((izq[0] + f * (abajo[0] - izq[0]), izq[1] + f * (abajo[1] - izq[1])),
              (arriba[0] + f * (der[0] - arriba[0]), arriba[1] + f * (der[1] - arriba[1])))
        linea((izq[0] + f * (arriba[0] - izq[0]), izq[1] + f * (arriba[1] - izq[1])),
              (abajo[0] + f * (der[0] - abajo[0]), abajo[1] + f * (der[1] - abajo[1])))
    poli([izq, arriba, der, abajo], fill="none", stroke="#1d1d1f", stroke_width="1")

    texto((0, 0), "Ca", "end", 16, "600")
    texto((L, 0), "Na+K", "start", 16, "600")
    texto((L / 2, h), "Mg", "middle", -8, "600")
    texto((L + sep, 0), "HCO₃+CO₃", "end", 16, "600")
    texto((2 * L + sep, 0), "Cl", "start", 16, "600")
    texto((L + sep + L / 2, h), "SO₄", "middle", -8, "600")
    texto(arriba, "SO₄+Cl · Ca+Mg", "middle", -10, "400", "#6e6e73")

    colores = ["#0071e3", "#ff9f0a", "#30b158", "#bf5af2", "#ff375f", "#64d2ff", "#8e8e93", "#ac8e68", "#5e5ce6", "#ffd60a"]
    leyenda = []
    n = 0
    for r in resultados:
        if not r.get("pct_cationes") or r["tipo"] == "—":
            continue
        pc, pa = r["pct_cationes"], r["pct_aniones"]
        c = cat_xy(pc["Ca"], pc["Mg"], pc["Na"] + pc["K"])
        a = an_xy(pa["HCO3"] + pa["CO3"], pa["SO4"], pa["Cl"])
        d = rombo(c, a)
        col = colores[n % len(colores)]
        for p in (c, a, d):
            x, y = P(*p)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{col}" fill-opacity="0.85" stroke="#fff" stroke-width="0.8"/>')
        leyenda.append((col, r["muestra"]))
        n += 1
    for i, (col, nombre) in enumerate(leyenda[:16]):
        y = 24 + i * 15
        out.append(f'<circle cx="18" cy="{y - 4}" r="4" fill="{col}"/>')
        out.append(f'<text x="28" y="{y}" fill="#1d1d1f">{nombre}</text>')
    out.append("</svg>")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return n


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Balance iónico, facies y diagrama de Piper.")
    p.add_argument("csv", help="CSV con iones mayores en mg/L")
    p.add_argument("--limite", type=float, default=5.0, help="Error aceptable en %% (por defecto 5; dudosa hasta el doble)")
    p.add_argument("--piper", default=None, help="Ruta de un SVG para el diagrama de Piper")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    if not filas:
        raise SystemExit("El archivo no tiene muestras.")
    cols = mapa_columnas(filas)
    minimos = [i for i in ("Ca", "Mg", "Na", "Cl", "SO4", "HCO3") if i not in cols]
    if minimos:
        raise SystemExit("Faltan columnas de iones mayores: " + ", ".join(minimos) +
                         ". Encabezados esperados: muestra, Ca, Mg, Na, K, HCO3, CO3, Cl, SO4, NO3 (mg/L).")
    res = [analizar(f, cols, delim, a.limite) for f in filas]
    n_piper = piper_svg(res, a.piper) if a.piper else 0

    if a.json:
        print(json.dumps({"limite_pct": a.limite, "muestras": res}, ensure_ascii=False, indent=2))
        return 0

    print(f"# Balance iónico: {a.csv}\n")
    print("| Muestra | Σ cationes (meq/L) | Σ aniones (meq/L) | Error (%) | Estado | Tipo de agua |")
    print("|---|---|---|---|---|---|")
    for r in res:
        e = "—" if r["error_pct"] is None else f"{r['error_pct']:+.1f}"
        print(f"| {r['muestra']} | {r['suma_cationes_meq']:.2f} | {r['suma_aniones_meq']:.2f} | {e} | {r['estado']} | {r['tipo']} |")
    cuenta = {}
    for r in res:
        cuenta[r["estado"]] = cuenta.get(r["estado"], 0) + 1
    print("\nResumen: " + ", ".join(f"{v} {k}" for k, v in cuenta.items()) +
          f". Criterio: aceptada hasta ±{a.limite:g} %, dudosa hasta ±{2 * a.limite:g} %.")
    detalle = [r for r in res if r.get("avisos") or r["faltan"] or r["bajo_limite"]]
    if detalle:
        print("\n## Observaciones\n")
        for r in detalle:
            notas = list(r.get("avisos", []))
            if r["faltan"]:
                notas.append("sin dato de " + ", ".join(r["faltan"]))
            if r["bajo_limite"]:
                notas.append("bajo el límite de detección: " + ", ".join(r["bajo_limite"]))
            print(f"- **{r['muestra']}**: " + "; ".join(notas) + ".")
    if a.piper:
        print(f"\nDiagrama de Piper guardado en {a.piper} ({n_piper} muestras).")
    print("\nError = 100·(Σcationes − Σaniones)/(Σcationes + Σaniones), en meq/L.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
