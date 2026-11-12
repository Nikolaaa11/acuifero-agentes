#!/usr/bin/env python3
"""Anonimiza una tabla antes de trabajarla con una IA, y revierte los resultados después.

Qué hace:
  - Reemplaza los nombres de pozos, puntos, faenas o clientes por códigos (P-001, P-002…).
  - Traslada las coordenadas a un origen local: se conservan distancias y geometría, no la ubicación.
  - Guarda la equivalencia en un archivo de clave (JSON) que queda SOLO en tu equipo.
  - Con --revertir, devuelve los nombres reales (y las coordenadas, si se indican) a cualquier archivo de texto.

Los valores medidos (niveles, concentraciones, fechas) no se alteran. Solo biblioteca estándar.

Ejemplos:
  python anonimizar.py niveles.csv --nombres punto --x este --y norte --clave clave-proyecto.json
  python anonimizar.py informe-anon.md --revertir --clave clave-proyecto.json --salida informe.md
"""
import argparse
import csv
import io
import json
import os
import re
import sys


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def leer_texto(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return f.read()


def delimitador(cabecera):
    if cabecera.count(";") > cabecera.count(","):
        return ";"
    if "\t" in cabecera and "," not in cabecera:
        return "\t"
    return ","


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


def escribir_numero(x, delim, decimales):
    t = f"{x:.{decimales}f}"
    return t.replace(".", ",") if delim != "," else t


def buscar(cabecera, nombre):
    for col in cabecera:
        if col.strip().lower() == nombre.strip().lower():
            return col
    raise SystemExit(f"No encuentro la columna «{nombre}». Columnas disponibles: " + ", ".join(cabecera))


def cargar_clave(ruta):
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return {"nombres": {}, "desplazamiento": None, "aviso": "Este archivo permite revertir el anonimizado. No lo compartas ni lo subas a ningún servicio."}


def anonimizar(a):
    texto = leer_texto(a.archivo)
    lineas = texto.splitlines()
    if not lineas:
        raise SystemExit("El archivo está vacío: " + a.archivo)
    delim = delimitador(lineas[0])
    lector = csv.DictReader(io.StringIO(texto), delimiter=delim)
    cab = lector.fieldnames or []
    filas = list(lector)
    col_nombres = [buscar(cab, n) for n in (a.nombres or [])]
    col_x = buscar(cab, a.x) if a.x else None
    col_y = buscar(cab, a.y) if a.y else None
    if not col_nombres and not col_x:
        raise SystemExit("Indica qué anonimizar: --nombres columna [columna…] y/o --x columna --y columna.")
    if bool(col_x) != bool(col_y):
        raise SystemExit("Las coordenadas se anonimizan de a pares: indica --x y también --y.")

    clave = cargar_clave(a.clave)
    nombres = clave["nombres"]
    nuevos = 0
    for f in filas:
        for col in col_nombres:
            real = (f[col] or "").strip()
            if not real:
                continue
            if real not in nombres:
                nombres[real] = f"{a.prefijo}-{len(nombres) + 1:03d}"
                nuevos += 1
            f[col] = nombres[real]
    movidas = 0
    if col_x:
        xs = [numero(f[col_x], delim) for f in filas]
        ys = [numero(f[col_y], delim) for f in filas]
        validos = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
        if validos and not clave["desplazamiento"]:
            clave["desplazamiento"] = {"x": min(x for x, _ in validos) - 1000.0, "y": min(y for _, y in validos) - 1000.0}
        d = clave["desplazamiento"]
        for f, x, y in zip(filas, xs, ys):
            if x is None or y is None or not d:
                continue
            f[col_x] = escribir_numero(x - d["x"], delim, a.decimales)
            f[col_y] = escribir_numero(y - d["y"], delim, a.decimales)
            movidas += 1

    salida = a.salida or (a.archivo.rsplit(".", 1)[0] + "-anon." + a.archivo.rsplit(".", 1)[-1])
    with open(salida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cab, delimiter=delim, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    with open(a.clave, "w", encoding="utf-8", newline="\n") as f:
        json.dump(clave, f, ensure_ascii=False, indent=2)
    resumen = {"salida": salida, "clave": a.clave, "nombres_reemplazados": len(nombres), "nombres_nuevos": nuevos,
               "coordenadas_trasladadas": movidas, "filas": len(filas)}
    if a.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return 0
    print(f"# Anonimizado: {a.archivo}\n")
    print(f"- Archivo anonimizado: {salida} ({len(filas)} filas)")
    print(f"- Nombres en la clave: {len(nombres)} ({nuevos} nuevos en esta corrida)")
    print(f"- Coordenadas trasladadas a un origen local: {movidas} puntos")
    print(f"- Clave para revertir: {a.clave}")
    print("\nLa clave queda solo en tu equipo: no la subas ni la pegues en ningún chat. "
          "Anonimizar reduce el riesgo, pero no reemplaza la autorización de tu empresa y del contrato para usar una IA con estos datos: "
          "los valores medidos siguen ahí y pueden bastar para reconocer un sitio.")
    return 0


def revertir(a):
    if not os.path.exists(a.clave):
        raise SystemExit("No encuentro la clave: " + a.clave)
    clave = cargar_clave(a.clave)
    texto = leer_texto(a.archivo)
    inverso = {cod: real for real, cod in clave["nombres"].items()}
    cuenta = 0
    if inverso:
        patron = re.compile("|".join(re.escape(c) for c in sorted(inverso, key=len, reverse=True)))

        def cambio(m):
            nonlocal cuenta
            cuenta += 1
            return inverso[m.group(0)]

        texto = patron.sub(cambio, texto)
    movidas = 0
    if a.x and a.y and clave.get("desplazamiento"):
        lineas = texto.splitlines()
        delim = delimitador(lineas[0])
        lector = csv.DictReader(io.StringIO(texto), delimiter=delim)
        cab = lector.fieldnames or []
        filas = list(lector)
        cx, cy = buscar(cab, a.x), buscar(cab, a.y)
        d = clave["desplazamiento"]
        for f in filas:
            x, y = numero(f[cx], delim), numero(f[cy], delim)
            if x is None or y is None:
                continue
            f[cx] = escribir_numero(x + d["x"], delim, a.decimales)
            f[cy] = escribir_numero(y + d["y"], delim, a.decimales)
            movidas += 1
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cab, delimiter=delim, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
        texto = buf.getvalue()
    salida = a.salida or (a.archivo.rsplit(".", 1)[0] + "-real." + a.archivo.rsplit(".", 1)[-1])
    with open(salida, "w", encoding="utf-8", newline="") as f:
        f.write(texto)
    resumen = {"salida": salida, "codigos_revertidos": cuenta, "coordenadas_restauradas": movidas}
    if a.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return 0
    print(f"# Revertido: {a.archivo}\n")
    print(f"- Archivo con nombres reales: {salida}")
    print(f"- Códigos reemplazados: {cuenta} · Coordenadas restauradas: {movidas}")
    print("\nRevisa el resultado antes de usarlo: si la IA abrevió o cambió un código (por ejemplo «P1» en vez de «P-001»), no se revierte solo.")
    return 0


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Anonimiza nombres y coordenadas de una tabla, y revierte los resultados.")
    p.add_argument("archivo", help="CSV a anonimizar, o archivo de texto a revertir")
    p.add_argument("--clave", required=True, help="Archivo JSON de la clave (se crea si no existe; guárdalo solo en tu equipo)")
    p.add_argument("--nombres", nargs="*", default=[], help="Columnas con nombres a reemplazar por códigos")
    p.add_argument("--x", default=None, help="Columna de coordenada este")
    p.add_argument("--y", default=None, help="Columna de coordenada norte")
    p.add_argument("--prefijo", default="P", help="Prefijo de los códigos (por defecto P)")
    p.add_argument("--decimales", type=int, default=2, help="Decimales de las coordenadas escritas (por defecto 2)")
    p.add_argument("--salida", default=None, help="Archivo de salida")
    p.add_argument("--revertir", action="store_true", help="Devuelve nombres reales (y coordenadas si se indican --x y --y)")
    p.add_argument("--json", action="store_true", help="Resumen en JSON")
    a = p.parse_args(argv)
    return revertir(a) if a.revertir else anonimizar(a)


if __name__ == "__main__":
    sys.exit(main())
