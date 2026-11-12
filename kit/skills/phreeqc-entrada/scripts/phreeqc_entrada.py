#!/usr/bin/env python3
"""Genera un archivo de entrada de PHREEQC a partir de una tabla de laboratorio.

Entrada: CSV con una fila por muestra y concentraciones en mg/L. Columnas reconocidas:
  muestra, pH, temp (°C), pe, densidad,
  Ca, Mg, Na, K, HCO3, CO3, alcalinidad (como CaCO3), Cl, SO4, NO3, F, SiO2,
  Fe, Mn, Al, Cu, Zn, Pb, Cd, Ba, Sr, Li, B, Br, As, Mo, Se, Sb, Ni, Co, Cr, U
Acepta separador coma o punto y coma, y coma decimal. Los valores «<x» se omiten.
Solo biblioteca estándar. Este script escribe el archivo; no ejecuta PHREEQC.

Salida: un archivo .pqi con un bloque SOLUTION por muestra y un SELECTED_OUTPUT
con pH, fuerza iónica, error de balance de cargas e índices de saturación.

Ejemplos:
  python phreeqc_entrada.py muestras.csv --salida muestras.pqi
  python phreeqc_entrada.py salmueras.csv --base pitzer.dat --salida salmueras.pqi
"""
import argparse
import csv
import json
import sys

# columna -> (línea PHREEQC, «as», está en phreeqc.dat, está en pitzer.dat, masa molar, carga)
ELEMENTOS = {
    "Ca": ("Ca", "", True, True, 40.078, 2), "Mg": ("Mg", "", True, True, 24.305, 2),
    "Na": ("Na", "", True, True, 22.990, 1), "K": ("K", "", True, True, 39.098, 1),
    "Cl": ("Cl", "", True, True, 35.453, 1), "SO4": ("S(6)", "as SO4", True, True, 96.06, 2),
    "NO3": ("N(5)", "as NO3", True, False, 62.005, 1), "F": ("F", "", True, False, 18.998, 1),
    "SiO2": ("Si", "as SiO2", True, True, 60.084, 0), "Fe": ("Fe", "", True, True, 55.845, 2),
    "Mn": ("Mn", "", True, True, 54.938, 2), "Al": ("Al", "", True, False, 26.982, 3),
    "Cu": ("Cu", "", True, False, 63.546, 2), "Zn": ("Zn", "", True, False, 65.38, 2),
    "Pb": ("Pb", "", True, False, 207.2, 2), "Cd": ("Cd", "", True, False, 112.41, 2),
    "Ba": ("Ba", "", True, True, 137.33, 2), "Sr": ("Sr", "", True, True, 87.62, 2),
    "Li": ("Li", "", True, True, 6.94, 1), "B": ("B", "", True, True, 10.81, 0),
    "Br": ("Br", "", True, True, 79.904, 1),
    "As": ("As", "", False, False, 74.922, 0), "Mo": ("Mo", "", False, False, 95.95, 0),
    "Se": ("Se", "", False, False, 78.97, 0), "Sb": ("Sb", "", False, False, 121.76, 0),
    "Ni": ("Ni", "", False, False, 58.693, 2), "Co": ("Co", "", False, False, 58.933, 2),
    "Cr": ("Cr", "", False, False, 51.996, 0), "U": ("U", "", False, False, 238.03, 0),
}
FASES = {
    "phreeqc.dat": ["Calcite", "Aragonite", "Dolomite", "Gypsum", "Anhydrite", "Halite", "Quartz", "Chalcedony",
                    "Fe(OH)3(a)", "Goethite", "Gibbsite", "Al(OH)3(a)", "Siderite", "Rhodochrosite", "Fluorite",
                    "Barite", "Celestite", "CO2(g)"],
    "pitzer.dat": ["Calcite", "Dolomite", "Gypsum", "Anhydrite", "Halite", "Sylvite", "CO2(g)"],
    "otras": ["Calcite", "Dolomite", "Gypsum", "Anhydrite", "Halite", "Quartz", "Chalcedony", "Goethite", "Gibbsite",
              "Siderite", "Fluorite", "Barite", "CO2(g)"],
}
ESPECIALES = {
    "muestra": ("muestra", "id", "punto", "pozo", "codigo", "código", "sample"),
    "ph": ("ph",), "temp": ("temp", "temperatura", "t", "t_c"), "pe": ("pe",),
    "densidad": ("densidad", "density", "rho"), "hco3": ("hco3",), "co3": ("co3",),
    "alcalinidad": ("alcalinidad", "alkalinity", "alc", "alcalinidad_caco3"),
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
    """Devuelve (valor, bajo_limite)."""
    v = (v or "").strip()
    if not v or v.lower() in ("nd", "n.d.", "-", "na", "n/a"):
        return None, False
    if v.startswith("<"):
        return None, True
    if delim != ",":
        v = v.replace(",", ".")
    try:
        return float(v), False
    except ValueError:
        return None, False


def mapa_columnas(filas):
    m = {}
    for col in filas[0].keys():
        if not col:
            continue
        base = col.strip().split("(")[0].split("[")[0].strip()
        clave = base.lower().replace("_mg_l", "").replace(" mg/l", "").replace("-", "").replace("+", "").strip()
        for canon, alias in ESPECIALES.items():
            if clave in alias and canon not in m:
                m[canon] = col
        for el in ELEMENTOS:
            if clave == el.lower() and el not in m:
                m[el] = col
    return m


def disponible(el, base):
    _, _, en_phreeqc, en_pitzer, _, _ = ELEMENTOS[el]
    if base == "phreeqc.dat":
        return en_phreeqc
    if base == "pitzer.dat":
        return en_pitzer
    return True


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Genera un archivo de entrada de PHREEQC desde una tabla de laboratorio.")
    p.add_argument("csv", help="CSV con una fila por muestra, en mg/L")
    p.add_argument("--salida", default=None, help="Archivo .pqi a escribir (por defecto, junto al CSV)")
    p.add_argument("--base", default="phreeqc.dat", help="Base de datos termodinámica: phreeqc.dat, pitzer.dat, wateq4f.dat, minteq.v4.dat, llnl.dat")
    p.add_argument("--temp", type=float, default=25.0, help="Temperatura en °C si la tabla no la trae (por defecto 25)")
    p.add_argument("--pe", type=float, default=4.0, help="pe supuesto si la tabla no lo trae (por defecto 4)")
    p.add_argument("--balancear", default=None, help="Elemento con el que cerrar el balance de cargas, por ejemplo Cl (por defecto, ninguno)")
    p.add_argument("--json", action="store_true", help="Resumen en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    if not filas:
        raise SystemExit("El archivo no tiene muestras.")
    c = mapa_columnas(filas)
    if "ph" not in c:
        raise SystemExit("Falta la columna pH: PHREEQC la necesita en cada solución.")
    if not any(el in c for el in ("Ca", "Na", "Cl", "SO4")):
        raise SystemExit("No encuentro iones mayores. Encabezados esperados: muestra, pH, Ca, Mg, Na, K, HCO3, Cl, SO4 (mg/L).")
    base = a.base.strip()
    fases = FASES.get(base, FASES["otras"])
    presentes = [el for el in ELEMENTOS if el in c]
    if "SiO2" not in presentes:
        fases = [f for f in fases if f not in ("Quartz", "Chalcedony")]
    if "Fe" not in presentes:
        fases = [f for f in fases if f not in ("Fe(OH)3(a)", "Goethite", "Siderite")]
    if "Al" not in presentes:
        fases = [f for f in fases if f not in ("Gibbsite", "Al(OH)3(a)")]
    if "Mn" not in presentes:
        fases = [f for f in fases if f != "Rhodochrosite"]
    if "F" not in presentes:
        fases = [f for f in fases if f != "Fluorite"]
    if "Ba" not in presentes:
        fases = [f for f in fases if f != "Barite"]
    if "Sr" not in presentes:
        fases = [f for f in fases if f != "Celestite"]

    ruta = a.salida or (a.csv.rsplit(".", 1)[0] + ".pqi")
    sel = ruta.rsplit(".", 1)[0] + ".sel"
    sel_nombre = sel.replace("\\", "/").split("/")[-1]
    avisos, omitidos, supuestos = [], set(), set()
    out = ["# Archivo de entrada de PHREEQC generado por la skill phreeqc-entrada del kit Acuífero.",
           "# Origen: " + a.csv.replace("\\", "/").split("/")[-1],
           "# Base de datos prevista: " + base + " (elígela al abrir o correr el archivo).",
           "# Revisa los supuestos marcados con «supuesto» antes de usar los resultados.", "",
           "TITLE Especiación e índices de saturación", "",
           "SELECTED_OUTPUT 1", "    -file " + sel_nombre, "    -reset false", "    -solution true", "    -pH true",
           "    -pe true", "    -temperature true", "    -ionic_strength true", "    -charge_balance true",
           "    -percent_error true", "    -saturation_indices " + " ".join(fases), ""]
    resumen = []
    for i, f in enumerate(filas):
        nombre = (f[c["muestra"]].strip() if "muestra" in c else "") or f"muestra {i + 1}"
        ph, _ = numero(f[c["ph"]], delim)
        if ph is None:
            avisos.append(f"{nombre}: sin pH; se omite la muestra")
            continue
        temp = numero(f[c["temp"]], delim)[0] if "temp" in c else None
        pe = numero(f[c["pe"]], delim)[0] if "pe" in c else None
        dens = numero(f[c["densidad"]], delim)[0] if "densidad" in c else None
        lin = [f"SOLUTION {len(resumen) + 1} {nombre}", "    units mg/l", f"    pH {ph:g}"]
        if temp is None:
            lin.append(f"    temp {a.temp:g}    # supuesto")
            supuestos.add(f"temperatura de {a.temp:g} °C")
        else:
            lin.append(f"    temp {temp:g}")
        if pe is None:
            lin.append(f"    pe {a.pe:g}    # supuesto")
            supuestos.add(f"pe de {a.pe:g}")
        else:
            lin.append(f"    pe {pe:g}")
        if dens is not None:
            lin.append(f"    density {dens / 1000.0 if dens > 5 else dens:g}")
        fuerza = 0.0
        escritos = 0
        # alcalinidad
        alc, _ = numero(f[c["alcalinidad"]], delim) if "alcalinidad" in c else (None, False)
        hco3, _ = numero(f[c["hco3"]], delim) if "hco3" in c else (None, False)
        co3, _ = numero(f[c["co3"]], delim) if "co3" in c else (None, False)
        if alc is not None:
            lin.append(f"    Alkalinity {alc:g} as CaCO3")
            fuerza += 0.5 * (alc / 50.04 / 1000.0)
        elif hco3 is not None or co3 is not None:
            total = (hco3 or 0.0) + (co3 or 0.0) * 2.0 * 61.0168 / 60.0089
            nota = "    # HCO3 más CO3 expresado como HCO3" if co3 else ""
            lin.append(f"    Alkalinity {total:.4g} as HCO3{nota}")
            fuerza += 0.5 * (total / 61.0168 / 1000.0)
        else:
            avisos.append(f"{nombre}: sin alcalinidad ni HCO3; el balance de cargas no cerrará")
        for el in presentes:
            v, bajo = numero(f[c[el]], delim)
            etiqueta, como, _, _, masa, carga = ELEMENTOS[el]
            if v is None:
                if bajo:
                    lin.append(f"    # {el}: bajo el límite de detección, no se incluye")
                continue
            if not disponible(el, base):
                lin.append(f"    # {el} {v:g}    # no está en {base}: usa otra base de datos para incluirlo")
                omitidos.add(el)
                continue
            extra = "    charge" if a.balancear and a.balancear.lower() == el.lower() else ""
            lin.append(f"    {etiqueta} {v:g}{(' ' + como) if como else ''}{extra}")
            fuerza += 0.5 * (v / masa / 1000.0) * carga ** 2
            escritos += 1
        lin.append("END")
        out.extend(lin + [""])
        resumen.append({"numero": len(resumen) + 1, "muestra": nombre, "elementos": escritos, "fuerza_ionica_aprox": fuerza})
        if fuerza > 1.0 and base != "pitzer.dat":
            avisos.append(f"{nombre}: fuerza iónica cercana a {fuerza:.1f} mol/L; para salmueras usa --base pitzer.dat")
    if not resumen:
        raise SystemExit("Ninguna muestra tenía pH: no se generó el archivo.")
    if omitidos:
        avisos.append("Elementos que " + base + " no incluye y quedaron como comentario: " + ", ".join(sorted(omitidos)) +
                      ". Para modelarlos usa una base que los contenga (por ejemplo wateq4f.dat o minteq.v4.dat).")
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))

    if a.json:
        print(json.dumps({"archivo": ruta, "base": base, "soluciones": resumen, "fases": fases,
                          "supuestos": sorted(supuestos), "avisos": avisos}, ensure_ascii=False, indent=2))
        return 0
    print(f"# Entrada de PHREEQC: {ruta}\n")
    print(f"- Soluciones escritas: {len(resumen)} · Base de datos prevista: {base}")
    print(f"- Índices de saturación pedidos: {', '.join(fases)}")
    print(f"- Los resultados quedarán en {sel_nombre} al correr el archivo.")
    if supuestos:
        print("- Supuestos: " + "; ".join(sorted(supuestos)) + ". Cámbialos si tienes el dato medido.")
    if avisos:
        print("\n## Avisos\n")
        for av in avisos:
            print("- " + av)
    print("\nEste script solo escribe el archivo; no ejecuta PHREEQC. Ábrelo con PHREEQC o con su interfaz, "
          "elige la base de datos indicada y revisa cada bloque antes de usar los resultados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
