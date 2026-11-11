#!/usr/bin/env python3
"""Empaqueta el kit para el sitio.

Lee kit/ y catalogo.json, valida que todo calce y genera:
  public/datos.js                         catálogo que usa la página
  public/descargas/acuifero-kit.zip       plugin completo (lo usan los instaladores)
  public/descargas/skills/<nombre>.zip    una skill por archivo, para subir a claude.ai
  public/img/                             resultados reales de los scripts con los datos de ejemplo

Uso: python tools/construir.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(RAIZ, "kit")
PUB = os.path.join(RAIZ, "public")
FECHA_ZIP = (2026, 1, 1, 0, 0, 0)
errores = []


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def partir(texto, ruta):
    """Separa el encabezado YAML del cuerpo. Solo admite name y description."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
    if not m:
        errores.append(f"{ruta}: no tiene encabezado")
        return {}, texto
    meta = {}
    for linea in m.group(1).splitlines():
        if not linea.strip():
            continue
        k, _, v = linea.partition(":")
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        meta[k.strip()] = v
    extra = set(meta) - {"name", "description"}
    if extra:
        errores.append(f"{ruta}: claves no admitidas en el encabezado: {sorted(extra)}")
    for k in ("name", "description"):
        if not meta.get(k):
            errores.append(f"{ruta}: falta {k}")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", meta.get("name", "")):
        errores.append(f"{ruta}: el nombre debe usar minúsculas, números y guiones (máximo 64)")
    if len(meta.get("description", "")) > 1024:
        errores.append(f"{ruta}: la descripción supera 1024 caracteres ({len(meta['description'])})")
    if '"' in meta.get("description", ""):
        errores.append(f"{ruta}: la descripción no puede llevar comillas dobles")
    return meta, m.group(2).strip()


def archivos_de(carpeta):
    out = []
    for base, dirs, files in os.walk(carpeta):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for f in sorted(files):
            if f.endswith(".pyc"):
                continue
            out.append(os.path.join(base, f))
    return out


def comprimir(destino, pares):
    """pares: lista de (ruta en disco, nombre dentro del zip). Zip reproducible."""
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta, nombre in sorted(pares, key=lambda p: p[1]):
            info = zipfile.ZipInfo(nombre.replace(os.sep, "/"), FECHA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(ruta, "rb") as f:
                datos = f.read()
            if ruta.endswith((".md", ".py", ".csv", ".json")):
                datos = datos.replace(b"\r\n", b"\n")
            z.writestr(info, datos)


def correr(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", env=env)


def main():
    cat = json.loads(leer(os.path.join(RAIZ, "catalogo.json")))
    etapas = {e["id"] for e in cat["etapas"]}
    apps = {a["id"] for a in cat["apps"]}
    calcs = {c["id"] for c in cat["calculadoras"]}

    # ---- Agentes ----
    agentes = []
    en_disco = sorted(f[:-3] for f in os.listdir(os.path.join(KIT, "agents")) if f.endswith(".md"))
    for extra in sorted(set(cat["agentes"]) - set(en_disco)):
        errores.append(f"catálogo: el agente {extra} no existe en kit/agents")
    for nombre in [n for n in cat["agentes"] if n in en_disco] + [n for n in en_disco if n not in cat["agentes"]]:
        ruta = os.path.join(KIT, "agents", nombre + ".md")
        meta, cuerpo = partir(leer(ruta), ruta)
        if meta.get("name") != nombre:
            errores.append(f"{ruta}: el nombre del encabezado no coincide con el archivo")
        c = cat["agentes"].get(nombre)
        if not c:
            errores.append(f"catálogo: falta el agente {nombre}")
            continue
        if c["etapa"] not in etapas:
            errores.append(f"catálogo: etapa desconocida en {nombre}")
        for a in c.get("apps", []):
            if a not in apps:
                errores.append(f"catálogo: app desconocida «{a}» en {nombre}")
        agentes.append({"id": nombre, "descripcion": meta.get("description", ""), "instrucciones": cuerpo,
                        "archivo": f"kit/agents/{nombre}.md", **c})

    # ---- Skills ----
    skills = []
    en_disco_s = sorted(d for d in os.listdir(os.path.join(KIT, "skills")) if os.path.isdir(os.path.join(KIT, "skills", d)))
    for extra in sorted(set(cat["skills"]) - set(en_disco_s)):
        errores.append(f"catálogo: la skill {extra} no existe en kit/skills")
    for nombre in [n for n in cat["skills"] if n in en_disco_s] + [n for n in en_disco_s if n not in cat["skills"]]:
        carpeta = os.path.join(KIT, "skills", nombre)
        ruta = os.path.join(carpeta, "SKILL.md")
        if not os.path.exists(ruta):
            errores.append(f"{carpeta}: falta SKILL.md")
            continue
        meta, cuerpo = partir(leer(ruta), ruta)
        if meta.get("name") != nombre:
            errores.append(f"{ruta}: el nombre del encabezado no coincide con la carpeta")
        c = cat["skills"].get(nombre)
        if not c:
            errores.append(f"catálogo: falta la skill {nombre}")
            continue
        if c.get("calculadora") and c["calculadora"] not in calcs:
            errores.append(f"catálogo: calculadora desconocida en {nombre}")
        archivos = [os.path.relpath(a, carpeta).replace(os.sep, "/") for a in archivos_de(carpeta)]
        skills.append({"id": nombre, "descripcion": meta.get("description", ""), "instrucciones": cuerpo,
                       "archivo": f"kit/skills/{nombre}/SKILL.md", "archivos": archivos, **c})
        comprimir(os.path.join(PUB, "descargas", "skills", nombre + ".zip"),
                  [(a, nombre + "/" + os.path.relpath(a, carpeta)) for a in archivos_de(carpeta)])

    ids_skills = {s["id"] for s in skills}
    ids_todos = ids_skills | {a["id"] for a in agentes}
    for a in agentes:
        for s in a.get("usa", []):
            if s not in ids_skills:
                errores.append(f"catálogo: {a['id']} usa la skill inexistente «{s}»")
    for r in cat["rutas"]:
        for p in r["pasos"]:
            if p not in ids_todos:
                errores.append(f"catálogo: la ruta {r['id']} menciona «{p}», que no existe")

    # Menciones cruzadas dentro de los textos: todo `nombre` entre acentos graves que parezca del kit debe existir
    for item in agentes + skills:
        for ref in re.findall(r"`((?:hidro|geo)-[a-z-]+)`", item["instrucciones"]):
            if ref not in ids_todos:
                errores.append(f"{item['archivo']}: menciona `{ref}`, que no existe")

    if errores:
        print("Errores:")
        for e in errores:
            print("  - " + e)
        return 1

    # ---- Pruebas ----
    r = correr([os.path.join(RAIZ, "tools", "probar_scripts.py")])
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print("Las pruebas de los scripts fallaron: no se empaqueta.")
        return 1
    n_pruebas = sum(1 for linea in r.stdout.splitlines() if linea.startswith("  bien"))
    n_web = 0
    if shutil.which("node"):
        rw = subprocess.run(["node", os.path.join(RAIZ, "tools", "probar_web.js")], capture_output=True, text=True, encoding="utf-8")
        if rw.returncode != 0:
            print(rw.stdout[-2000:])
            print("Las pruebas de las calculadoras fallaron: no se empaqueta.")
            return 1
        n_web = sum(1 for linea in rw.stdout.splitlines() if linea.startswith("  bien"))

    # ---- Zip del kit (raíz del plugin) ----
    comprimir(os.path.join(PUB, "descargas", "acuifero-kit.zip"),
              [(a, os.path.relpath(a, KIT)) for a in archivos_de(KIT)])

    # ---- Imágenes de muestra: salidas reales de los scripts con los datos de ejemplo ----
    img = os.path.join(PUB, "img")
    os.makedirs(img, exist_ok=True)
    sk = os.path.join(KIT, "skills")
    correr([os.path.join(sk, "balance-ionico", "scripts", "balance_ionico.py"),
            os.path.join(sk, "balance-ionico", "ejemplos", "hidroquimica.csv"), "--piper", os.path.join(img, "piper.svg")])
    tmp = os.path.join(img, "_piezo")
    correr([os.path.join(sk, "mapa-piezometrico", "scripts", "piezometria.py"),
            os.path.join(sk, "mapa-piezometrico", "ejemplos", "piezometria.csv"), "--intervalo", "5", "--salida", tmp])
    if os.path.exists(os.path.join(tmp, "vista.svg")):
        os.replace(os.path.join(tmp, "vista.svg"), os.path.join(img, "piezometria.svg"))
    for f in ("curvas.geojson", "grilla.asc"):
        if os.path.exists(os.path.join(tmp, f)):
            os.remove(os.path.join(tmp, f))
    if os.path.isdir(tmp):
        os.rmdir(tmp)
    salidas = {}
    for clave, args in {
        "ensayo-bombeo": [os.path.join(sk, "ensayo-bombeo", "scripts", "ensayo_bombeo.py"),
                          os.path.join(sk, "ensayo-bombeo", "ejemplos", "ensayo-bombeo.csv"), "--q", "12", "--r", "35", "--b", "40"],
        "balance-ionico": [os.path.join(sk, "balance-ionico", "scripts", "balance_ionico.py"),
                           os.path.join(sk, "balance-ionico", "ejemplos", "hidroquimica.csv")],
        "tendencia-niveles": [os.path.join(sk, "tendencia-niveles", "scripts", "tendencia.py"),
                              os.path.join(sk, "tendencia-niveles", "ejemplos", "niveles-monitoreo.csv"), "--unidad", "m"],
        "calibracion-modelo": [os.path.join(sk, "calibracion-modelo", "scripts", "calibracion.py"),
                               os.path.join(sk, "calibracion-modelo", "ejemplos", "calibracion.csv")],
    }.items():
        out = correr(args).stdout
        # Rutas del equipo fuera del texto publicado
        out = re.sub(r"^# (.+?): .*$", lambda m: "# " + m.group(1), out, count=1, flags=re.M)
        salidas[clave] = out.strip()

    datos = {
        "version": cat["version"], "repo": cat["repo"], "sitio": cat["sitio"],
        "etapas": cat["etapas"], "agentes": agentes, "skills": skills, "apps": cat["apps"],
        "calculadoras": cat["calculadoras"], "rutas": cat["rutas"], "pruebas": n_pruebas, "pruebas_web": n_web, "salidas": salidas,
    }
    with open(os.path.join(PUB, "datos.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("// Generado por tools/construir.py a partir de kit/ y catalogo.json. No editar a mano.\n")
        f.write("window.ACUIFERO = " + json.dumps(datos, ensure_ascii=False, indent=1) + ";\n")

    kb = os.path.getsize(os.path.join(PUB, "descargas", "acuifero-kit.zip")) / 1024
    print(f"Listo: {len(agentes)} agentes, {len(skills)} skills, {n_pruebas} + {n_web} pruebas, kit de {kb:.0f} KB.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
