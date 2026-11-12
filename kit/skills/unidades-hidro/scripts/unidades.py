#!/usr/bin/env python3
"""Conversor de unidades de uso diario en hidrogeología.

Magnitudes: conductividad hidráulica (K), caudal (Q), transmisividad (T),
longitud, área y volumen. Solo usa la biblioteca estándar de Python.

Ejemplos:
  python unidades.py 1e-5 m/s m/d
  python unidades.py 12 L/s m3/d
  python unidades.py 450 m2/d m2/s
  python unidades.py --lista
"""
import argparse
import sys

DIA = 86400.0
ANO = 365.25 * DIA
GAL = 0.003785411784  # galón de EE. UU. en m3
PIE = 0.3048

# Factor para pasar cada unidad a la unidad base de su magnitud
UNIDADES = {
    "conductividad hidráulica (base m/s)": {
        "m/s": 1.0, "cm/s": 0.01, "mm/s": 0.001, "m/h": 1 / 3600.0, "m/d": 1 / DIA, "cm/d": 0.01 / DIA,
        "mm/d": 0.001 / DIA, "m/año": 1 / ANO, "mm/año": 0.001 / ANO, "ft/d": PIE / DIA, "gpd/ft2": GAL / DIA / PIE ** 2,
    },
    "caudal (base m3/s)": {
        "m3/s": 1.0, "L/s": 0.001, "L/min": 0.001 / 60, "m3/h": 1 / 3600.0, "m3/d": 1 / DIA,
        "m3/año": 1 / ANO, "hm3/año": 1e6 / ANO, "Mm3/año": 1e6 / ANO, "gpm": GAL / 60.0, "ft3/s": PIE ** 3,
    },
    "transmisividad (base m2/s)": {
        "m2/s": 1.0, "m2/h": 1 / 3600.0, "m2/d": 1 / DIA, "cm2/s": 1e-4, "ft2/d": PIE ** 2 / DIA, "gpd/ft": GAL / DIA / PIE,
    },
    "longitud (base m)": {"m": 1.0, "cm": 0.01, "mm": 0.001, "km": 1000.0, "ft": 0.3048, "in": 0.0254},
    "área (base m2)": {"m2": 1.0, "ha": 1e4, "km2": 1e6, "acre": 4046.8564},
    "volumen (base m3)": {"m3": 1.0, "L": 0.001, "hm3": 1e6, "Mm3": 1e6, "gal": GAL, "acre-ft": 1233.4818},
}
SINONIMOS = (("m^3", "m3"), ("m³", "m3"), ("m^2", "m2"), ("m²", "m2"), ("ft^2", "ft2"), ("ft²", "ft2"),
             ("/día", "/d"), ("/dia", "/d"), ("/day", "/d"), ("/ano", "/año"), ("/anio", "/año"),
             ("/year", "/año"), ("/yr", "/año"), ("/seg", "/s"), ("/hr", "/h"))


def normalizar(u):
    u = u.strip().replace(" ", "")
    bajo = u.lower()
    for viejo, nuevo in SINONIMOS:
        bajo = bajo.replace(viejo, nuevo)
    if bajo.endswith("/a"):
        bajo += "ño"
    for tabla in UNIDADES.values():
        for nombre in tabla:
            if nombre.lower() == bajo:
                return nombre
    return u


def convertir(valor, desde, hacia):
    d, h = normalizar(desde), normalizar(hacia)
    for magnitud, tabla in UNIDADES.items():
        if d in tabla and h in tabla:
            return valor * tabla[d] / tabla[h], magnitud.split(" (")[0], d, h
    md = [m for m, t in UNIDADES.items() if d in t]
    mh = [m for m, t in UNIDADES.items() if h in t]
    if not md:
        raise ValueError(f"No conozco la unidad «{desde}». Usa --lista para ver las disponibles.")
    if not mh:
        raise ValueError(f"No conozco la unidad «{hacia}». Usa --lista para ver las disponibles.")
    raise ValueError(f"«{desde}» es de {md[0].split(' (')[0]} y «{hacia}» es de {mh[0].split(' (')[0]}: no se pueden convertir entre sí.")


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Conversor de unidades para hidrogeología.")
    p.add_argument("valor", nargs="?", type=float)
    p.add_argument("desde", nargs="?")
    p.add_argument("hacia", nargs="?")
    p.add_argument("--lista", action="store_true", help="Muestra las unidades disponibles")
    a = p.parse_args(argv)
    if a.lista or a.valor is None or not a.desde or not a.hacia:
        for magnitud, tabla in UNIDADES.items():
            print(f"{magnitud}: " + ", ".join(tabla))
        return 0 if a.lista else 2
    try:
        r, magnitud, d, h = convertir(a.valor, a.desde, a.hacia)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"{a.valor:g} {d} = {r:.6g} {h}  ({magnitud})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
