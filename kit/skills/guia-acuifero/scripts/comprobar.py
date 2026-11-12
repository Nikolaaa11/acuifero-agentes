#!/usr/bin/env python3
"""Comprueba que el kit Acuífero quedó bien instalado.

Corre cada script de cálculo con sus datos de ejemplo y compara el resultado con el valor esperado.
No modifica nada: los archivos que genera van a una carpeta temporal que se borra al terminar.

Uso:
  python comprobar.py            informe completo
  python comprobar.py --breve    una sola línea (lo usa el instalador)
"""
import json
import os
import subprocess
import sys
import tempfile

SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def salida_utf8():
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def correr(skill, script, *args):
    ruta = os.path.join(SKILLS, skill, "scripts", script)
    if not os.path.exists(ruta):
        return None, "no está instalado"
    try:
        r = subprocess.run([sys.executable, ruta, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:  # noqa: BLE001
        return None, f"no se pudo ejecutar ({e.__class__.__name__})"
    if r.returncode != 0:
        ultima = (r.stderr or r.stdout or "").strip().splitlines()
        return None, "error: " + (ultima[-1][:120] if ultima else "sin mensaje")
    return r.stdout, ""


def ej(skill, nombre):
    return os.path.join(SKILLS, skill, "ejemplos", nombre)


def cerca(a, b, rel):
    return a is not None and abs(a - b) <= rel * abs(b)


def pruebas(tmp):
    """Cada prueba devuelve (nombre, bien, detalle)."""
    out = []

    def caso(nombre, skill, script, args, validar):
        salida, err = correr(skill, script, *args)
        if salida is None:
            out.append((nombre, False, err))
            return
        try:
            bien, detalle = validar(salida)
        except Exception as e:  # noqa: BLE001
            bien, detalle = False, f"resultado inesperado ({e.__class__.__name__})"
        out.append((nombre, bien, detalle))

    def v_bombeo(s):
        t = next(x for x in json.loads(s)["resultados"] if x["metodo"] == "Theis")["T_m2_d"]
        return cerca(t, 450, 0.03), f"T = {t:.0f} m²/d (esperado 450)"
    caso("Ensayo de bombeo", "ensayo-bombeo", "ensayo_bombeo.py",
         [ej("ensayo-bombeo", "ensayo-bombeo.csv"), "--q", "12", "--r", "35", "--b", "40", "--json"], v_bombeo)

    def v_ionico(s):
        m = {x["muestra"]: x for x in json.loads(s)["muestras"]}
        return m["PZ-05"]["estado"] == "rechazada" and m["PZ-01"]["estado"] == "aceptada", f"PZ-05 {m['PZ-05']['estado']}, PZ-01 {m['PZ-01']['estado']}"
    caso("Balance iónico", "balance-ionico", "balance_ionico.py", [ej("balance-ionico", "hidroquimica.csv"), "--json"], v_ionico)

    def v_tendencia(s):
        p = {x["punto"]: x for x in json.loads(s)["puntos"]}
        return p["PM-01"]["tendencia"] == "decreciente", f"PM-01 {p['PM-01']['tendencia']} ({p['PM-01']['sen_por_ano']:.2f} m/año)"
    caso("Tendencias", "tendencia-niveles", "tendencia.py", [ej("tendencia-niveles", "niveles-monitoreo.csv"), "--json"], v_tendencia)

    def v_piezo(s):
        r = json.loads(s)
        return r["rumbo_flujo"] == "SO" and len(r["curvas"]) >= 4, f"flujo hacia el {r['rumbo_flujo']}, {len(r['curvas'])} curvas"
    caso("Mapa piezométrico", "mapa-piezometrico", "piezometria.py",
         [ej("mapa-piezometrico", "piezometria.csv"), "--salida", os.path.join(tmp, "piezo"), "--json"], v_piezo)

    def v_calib(s):
        t = json.loads(s)["total"]
        return t["n"] == 18 and t["rmse"] > 0, f"{t['n']} puntos, RMSE {t['rmse']:.2f} m"
    caso("Calibración de modelos", "calibracion-modelo", "calibracion.py", [ej("calibracion-modelo", "calibracion.csv"), "--json"], v_calib)

    caso("Unidades", "unidades-hidro", "unidades.py", ["1e-5", "m/s", "m/d"], lambda s: ("0.864 m/d" in s, s.strip()[:40]))

    def v_aba(s):
        d = json.loads(s)
        m = {x["muestra"]: x for x in d["muestras"]}
        return m["MR-07"]["clase"] == "generador" and m["MR-01"]["clase"] == "no generador", f"{d['resumen']['generador']} generadoras, {d['resumen']['no generador']} no generadoras"
    caso("Balance ácido-base", "balance-acido-base", "aba.py", [ej("balance-acido-base", "ensayos-estaticos.csv"), "--json"], v_aba)

    def v_phreeqc(s):
        d = json.loads(s)
        with open(d["archivo"], encoding="utf-8") as f:
            texto = f.read()
        return len(d["soluciones"]) == 6 and texto.count("\nSOLUTION ") == 6 and "SELECTED_OUTPUT" in texto, f"{len(d['soluciones'])} soluciones escritas"
    caso("Entrada de PHREEQC", "phreeqc-entrada", "phreeqc_entrada.py",
         [ej("phreeqc-entrada", "aguas.csv"), "--salida", os.path.join(tmp, "aguas.pqi"), "--json"], v_phreeqc)

    def v_aguas(s):
        p = json.loads(s)["periodos"]
        return p["2025-01"]["estado"] == "cierra" and p["2025-02"]["estado"] == "revisar", f"enero {p['2025-01']['estado']}, febrero {p['2025-02']['estado']}"
    caso("Balance de aguas", "balance-aguas", "balance_aguas.py", [ej("balance-aguas", "balance-relaves.csv"), "--json"], v_aguas)

    def v_carga(s):
        p = {x["punto"]: x for x in json.loads(s)["puntos"]}
        return cerca(p["SB-01"]["carga_equivalente"], 2304.7025, 1e-6), f"SB-01 = {p['SB-01']['carga_equivalente']:.2f} m s. n. m."
    caso("Salares: carga equivalente", "salares", "salares.py", ["carga", ej("salares", "niveles-densidad.csv"), "--json"], v_carga)

    def v_evap(s):
        a = json.loads(s)["ajuste"]
        return cerca(a["E0_mm_d"], 6.0, 0.08) and cerca(a["k_por_m"], 2.5, 0.08), f"E₀ = {a['E0_mm_d']:.2f} mm/d, k = {a['k_por_m']:.2f} por metro"
    caso("Salares: evaporación", "salares", "salares.py", ["evaporacion", ej("salares", "evaporacion.csv"), "--json"], v_evap)

    def v_umbrales(s):
        p = {x["punto"]: x for x in json.loads(s)["puntos"]}
        return p["PC-01"]["estado"] == "alerta" and p["QC-04"]["estado"] == "acción", f"PC-01 en {p['PC-01']['estado']}, QC-04 en {p['QC-04']['estado']}"
    caso("Umbrales de alerta", "umbrales-alerta", "umbrales.py",
         [ej("umbrales-alerta", "series.csv"), ej("umbrales-alerta", "umbrales.csv"), "--json"], v_umbrales)

    def v_anon(s):
        d = json.loads(s)
        clave = os.path.join(tmp, "clave.json")
        vuelta, err = correr("anonimizar-datos", "anonimizar.py", d["salida"], "--revertir", "--clave", clave, "--x", "este", "--y", "norte",
                             "--salida", os.path.join(tmp, "vuelta.csv"), "--json")
        if vuelta is None:
            return False, err
        with open(ej("anonimizar-datos", "pozos.csv"), encoding="utf-8") as f:
            original = f.read().strip().replace("\r\n", "\n")
        with open(os.path.join(tmp, "vuelta.csv"), encoding="utf-8") as f:
            recuperado = f.read().strip().replace("\r\n", "\n")
        with open(d["salida"], encoding="utf-8") as f:
            anonimo = f.read()
        return recuperado == original and "Pozo" not in anonimo, f"{d['nombres_reemplazados']} nombres ocultos y recuperados"
    caso("Anonimizar datos", "anonimizar-datos", "anonimizar.py",
         [ej("anonimizar-datos", "pozos.csv"), "--nombres", "punto", "--x", "este", "--y", "norte", "--clave", os.path.join(tmp, "clave.json"),
          "--salida", os.path.join(tmp, "anon.csv"), "--json"], v_anon)
    return out


def main():
    salida_utf8()
    breve = "--breve" in sys.argv
    if sys.version_info < (3, 8):
        print(f"Python {sys.version_info.major}.{sys.version_info.minor} es muy antiguo: el kit necesita Python 3.8 o posterior.")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        res = pruebas(tmp)
    bien = sum(1 for _, b, _ in res if b)
    carpetas = [d for d in os.listdir(SKILLS) if os.path.exists(os.path.join(SKILLS, d, "SKILL.md"))]
    dir_agentes = os.path.join(os.path.dirname(SKILLS), "agents")
    agentes = [f for f in os.listdir(dir_agentes) if f.endswith(".md") and f.startswith(("hidro-", "geo-"))] if os.path.isdir(dir_agentes) else []
    if breve:
        if bien == len(res):
            print(f"Comprobación: los {len(res)} cálculos funcionan (Python {sys.version_info.major}.{sys.version_info.minor}).")
        else:
            fallas = ", ".join(n for n, b, _ in res if not b)
            print(f"Comprobación: {bien} de {len(res)} cálculos funcionan. Fallan: {fallas}.")
        return 0 if bien == len(res) else 1
    print("Comprobación del kit Acuífero\n")
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"  Carpeta de skills: {SKILLS}")
    print(f"  Skills encontradas: {len(carpetas)}" + (f" · Agentes encontrados: {len(agentes)}" if agentes else ""))
    print()
    for nombre, b, detalle in res:
        print(("  bien   " if b else "  FALLA  ") + nombre.ljust(28) + detalle)
    print()
    if bien == len(res):
        print(f"Todo funciona: los {len(res)} cálculos dieron el resultado esperado.")
        print("Siguiente paso: abre Claude y escribe «¿Qué agentes del kit Acuífero tengo disponibles?».")
        return 0
    print(f"{len(res) - bien} de {len(res)} cálculos no funcionaron. Vuelve a correr el instalador; si sigue igual, revisa «Si algo falla» en el manual.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
