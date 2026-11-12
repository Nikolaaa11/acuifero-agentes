#!/usr/bin/env python3
"""Interpretación de ensayos de bombeo a caudal constante.

Métodos: Cooper-Jacob (recta en semilog), Theis (ajuste por mínimos cuadrados)
y recuperación de Theis. Solo usa la biblioteca estándar de Python.

Entrada: CSV con columnas t_min (minutos desde el inicio del bombeo) y
s_m (descenso en metros). Acepta separador coma o punto y coma, y coma decimal.

Ejemplos:
  python ensayo_bombeo.py datos.csv --q 12 --r 35 --b 40
  python ensayo_bombeo.py recuperacion.csv --q 12 --recuperacion --tp 1440
"""
import argparse
import csv
import json
import math
import sys

EULER = 0.5772156649015329
ALIAS_T = ("t_min", "tiempo_min", "t", "tiempo", "minutos")
ALIAS_S = ("s_m", "descenso_m", "s", "descenso", "abatimiento_m", "abatimiento")


def w_theis(u):
    """Función de pozo de Theis, W(u) = E1(u)."""
    if u <= 0:
        raise ValueError("u debe ser positivo")
    if u < 1.0:
        suma = -EULER - math.log(u)
        termino = u  # u^n / n!
        signo = 1.0
        n = 1
        while n < 200:
            aporte = signo * termino / n
            suma += aporte
            if abs(aporte) < 1e-17:
                break
            n += 1
            termino *= u / n
            signo = -signo
        return suma
    if u > 700:
        return 0.0
    # Fracción continua (Lentz modificado)
    b = u + 1.0
    c = 1e300
    d = 1.0 / b
    h = d
    for i in range(1, 300):
        an = -float(i * i)
        b += 2.0
        d = 1.0 / (an * d + b)
        c = b + an / c
        delta = c * d
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h * math.exp(-u)


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
    filas = list(csv.DictReader(lineas, delimiter=delim))
    return filas, delim


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
    if not filas:
        return None
    for nombre in filas[0].keys():
        if nombre and nombre.strip().lower() in alias:
            return nombre
    return None


def regresion(x, y):
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    if sxx == 0:
        raise ValueError("Todos los tiempos son iguales")
    m = sxy / sxx
    a0 = my - m * mx
    ss_res = sum((b - (a0 + m * a)) ** 2 for a, b in zip(x, y))
    ss_tot = sum((b - my) ** 2 for b in y)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return a0, m, r2


def cooper_jacob(t_d, s, q, r, tmin=None, tmax=None, u_max=0.05):
    """Ajusta la recta de Cooper-Jacob. t_d en días, q en m3/d. Devuelve dict."""
    pares = [(t, d) for t, d in zip(t_d, s) if t > 0 and d > 0]
    if tmin is not None:
        pares = [p for p in pares if p[0] >= tmin]
    if tmax is not None:
        pares = [p for p in pares if p[0] <= tmax]
    manual = tmin is not None or tmax is not None
    usados = pares
    T = S = t0 = None
    r2 = float("nan")
    m = None
    for _ in range(8):
        if len(usados) < 3:
            break
        a0, m, r2 = regresion([math.log10(p[0]) for p in usados], [p[1] for p in usados])
        if m <= 0:
            break
        T = 2.302585 * q / (4.0 * math.pi * m)
        t0 = 10 ** (-a0 / m)
        S = 2.25 * T * t0 / r ** 2 if r else None
        if manual or not S:
            break
        nuevos = [p for p in pares if r ** 2 * S / (4.0 * T * p[0]) < u_max]
        if len(nuevos) < 3 or len(nuevos) == len(usados):
            break
        usados = nuevos
    if T is None or m is None or m <= 0:
        return None
    u_peor = max(r ** 2 * S / (4.0 * T * p[0]) for p in usados) if S else None
    return {
        "metodo": "Cooper-Jacob",
        "T_m2_d": T,
        "S": S,
        "pendiente_m_por_ciclo": m,
        "t0_min": t0 * 1440.0,
        "r2": r2,
        "puntos_usados": len(usados),
        "t_desde_min": usados[0][0] * 1440.0,
        "t_hasta_min": usados[-1][0] * 1440.0,
        "u_maximo": u_peor,
    }


def nelder_mead(f, x0, paso=0.5, iteraciones=400, tol=1e-12):
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        p = list(x0)
        p[i] += paso
        simplex.append(p)
    valores = [f(p) for p in simplex]
    for _ in range(iteraciones):
        orden = sorted(range(n + 1), key=lambda i: valores[i])
        simplex = [simplex[i] for i in orden]
        valores = [valores[i] for i in orden]
        if abs(valores[-1] - valores[0]) < tol:
            break
        centro = [sum(p[i] for p in simplex[:-1]) / n for i in range(n)]
        peor = simplex[-1]
        refl = [centro[i] + (centro[i] - peor[i]) for i in range(n)]
        f_refl = f(refl)
        if valores[0] <= f_refl < valores[-2]:
            simplex[-1], valores[-1] = refl, f_refl
            continue
        if f_refl < valores[0]:
            exp = [centro[i] + 2.0 * (centro[i] - peor[i]) for i in range(n)]
            f_exp = f(exp)
            if f_exp < f_refl:
                simplex[-1], valores[-1] = exp, f_exp
            else:
                simplex[-1], valores[-1] = refl, f_refl
            continue
        contr = [centro[i] + 0.5 * (peor[i] - centro[i]) for i in range(n)]
        f_contr = f(contr)
        if f_contr < valores[-1]:
            simplex[-1], valores[-1] = contr, f_contr
            continue
        mejor = simplex[0]
        simplex = [mejor] + [[mejor[i] + 0.5 * (p[i] - mejor[i]) for i in range(n)] for p in simplex[1:]]
        valores = [valores[0]] + [f(p) for p in simplex[1:]]
    i = min(range(n + 1), key=lambda k: valores[k])
    return simplex[i], valores[i]


def descenso_theis(q, T, S, r, t_d):
    u = r ** 2 * S / (4.0 * T * t_d)
    return q / (4.0 * math.pi * T) * w_theis(u)


def theis(t_d, s, q, r, inicio=None):
    """Ajuste de T y S por mínimos cuadrados. Requiere r."""
    pares = [(t, d) for t, d in zip(t_d, s) if t > 0 and d > 0]
    if len(pares) < 4:
        return None
    T0, S0 = inicio if inicio and inicio[0] and inicio[1] else (100.0, 1e-3)

    def error(p):
        T = math.exp(p[0])
        S = math.exp(p[1])
        if not (1e-6 < T < 1e8 and 1e-12 < S < 1.0):
            return 1e30
        return sum((d - descenso_theis(q, T, S, r, t)) ** 2 for t, d in pares)

    mejor, sse = nelder_mead(error, [math.log(T0), math.log(S0)])
    mejor, sse = nelder_mead(error, mejor, paso=0.1)
    T = math.exp(mejor[0])
    S = math.exp(mejor[1])
    n = len(pares)
    media = sum(d for _, d in pares) / n
    ss_tot = sum((d - media) ** 2 for _, d in pares)
    return {
        "metodo": "Theis",
        "T_m2_d": T,
        "S": S,
        "rmse_m": math.sqrt(sse / n),
        "r2": 1.0 - sse / ss_tot if ss_tot > 0 else float("nan"),
        "puntos_usados": n,
    }


def recuperacion(t_d, s_res, q, tp_d):
    """Recuperación de Theis: descenso residual contra log10(t/t')."""
    x, y = [], []
    for t, d in zip(t_d, s_res):
        tprima = t - tp_d
        if tprima > 0 and d > 0:
            x.append(math.log10(t / tprima))
            y.append(d)
    if len(x) < 3:
        return None
    # Se usa el tramo final (t/t' pequeño), donde vale la aproximación logarítmica
    orden = sorted(range(len(x)), key=lambda i: x[i])
    corte = max(3, int(len(orden) * 0.7))
    idx = orden[:corte]
    a0, m, r2 = regresion([x[i] for i in idx], [y[i] for i in idx])
    if m <= 0:
        return None
    return {
        "metodo": "Recuperación de Theis",
        "T_m2_d": 2.302585 * q / (4.0 * math.pi * m),
        "S": None,
        "pendiente_m_por_ciclo": m,
        "descenso_residual_en_t_t1": a0,
        "r2": r2,
        "puntos_usados": len(idx),
        "tt_desde": 10 ** x[idx[0]],
        "tt_hasta": 10 ** x[idx[-1]],
    }


def diagnostico(t_d, s, q):
    """Derivada del descenso respecto de ln(t) (Bourdet) y lectura del tramo final."""
    pares = [(math.log(t), d) for t, d in zip(t_d, s) if t > 0 and d > 0]
    der = []
    for i in range(1, len(pares) - 1):
        (x0, s0), (x1, s1), (x2, s2) = pares[i - 1], pares[i], pares[i + 1]
        d1, d2 = x1 - x0, x2 - x1
        if d1 <= 0 or d2 <= 0:
            continue
        der.append((math.exp(x1), ((s1 - s0) / d1 * d2 + (s2 - s1) / d2 * d1) / (d1 + d2)))
    if len(der) < 6:
        return None

    def mediana(lista):
        lista = sorted(lista)
        k = len(lista) // 2
        return lista[k] if len(lista) % 2 else (lista[k - 1] + lista[k]) / 2.0

    n = len(der)
    tercio = max(2, n // 3)
    medio = mediana([v for _, v in der[n - 2 * tercio:n - tercio]])
    final = mediana([v for _, v in der[-tercio:]])
    if final <= 0:
        lectura = ("La derivada final es nula o negativa: el nivel se estabilizó. Indica recarga, goteo fuerte "
                   "o un borde de nivel constante; Theis no describe ese tramo.")
    else:
        cambio = (final - medio) / medio if medio > 0 else 0.0
        if abs(cambio) <= 0.25:
            lectura = "Derivada estable en el tramo final: flujo radial de acción infinita. Theis y Cooper-Jacob son aplicables ahí."
        elif cambio < 0:
            lectura = ("La derivada cae en el tramo final: posible goteo, recarga o borde de nivel constante. "
                       "Ajustar ese tramo con Theis sobreestima T.")
        else:
            lectura = ("La derivada sube en el tramo final: posible borde impermeable, acuífero limitado o caudal en aumento. "
                       "Revisa antes de adoptar un solo valor de T.")
    return {
        "derivada_tramo_medio_m": medio,
        "derivada_tramo_final_m": final,
        "T_derivada_m2_d": q / (4.0 * math.pi * final) if final > 0 else None,
        "lectura": lectura,
        "derivada": [{"t_min": t * 1440.0, "ds_dlnt_m": v} for t, v in der],
    }


def fmt(v, cifras=3):
    if v is None:
        return "—"
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return "—"
    if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e5):
        return f"{v:.{cifras - 1}e}".replace("e-0", "e-").replace("e+0", "e")
    if abs(v) >= 10 ** cifras:
        return f"{v:.0f}"
    return f"{v:.{cifras}g}"


def advertencias(res, r, pozo_bombeo, n):
    avisos = []
    if n < 8:
        avisos.append(f"Solo hay {n} lecturas válidas: el ajuste es poco robusto.")
    if not r:
        avisos.append("Sin distancia r no se puede calcular el almacenamiento S.")
    if pozo_bombeo:
        avisos.append("Datos del pozo de bombeo: T es utilizable, S no es confiable (pérdidas de pozo y radio efectivo).")
    for x in res:
        S = x.get("S")
        if S is not None and not (1e-6 <= S <= 0.4):
            avisos.append(f"{x['metodo']}: S = {fmt(S)} está fuera del rango físico habitual (1e-6 a 0,4). Revisa r, unidades y el modelo elegido.")
        if x["metodo"] == "Cooper-Jacob" and x.get("u_maximo") is not None and x["u_maximo"] > 0.05:
            avisos.append(f"Cooper-Jacob: u llega a {fmt(x['u_maximo'])} en el tramo usado (debe ser menor que 0,05). Usa tiempos más largos o Theis.")
        if x.get("r2") is not None and not math.isnan(x["r2"]) and x["r2"] < 0.95:
            avisos.append(f"{x['metodo']}: R² = {x['r2']:.3f}. El modelo no describe bien los datos; revisa bordes, goteo o caudal variable.")
    ts = [x["T_m2_d"] for x in res if x.get("T_m2_d")]
    if len(ts) >= 2 and max(ts) / min(ts) > 1.5:
        avisos.append("Los métodos difieren en T más de 50 %. Mira el gráfico de diagnóstico antes de elegir un valor.")
    return avisos


def graficar(ruta, t_min, s, res, q, r):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("Aviso: matplotlib no está instalado; no se generó el gráfico.", file=sys.stderr)
        return False
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    ax.semilogx(t_min, s, "o", ms=4, color="#1d1d1f", label="Medido")
    tt = [min(t_min) * (max(t_min) / min(t_min)) ** (i / 120) for i in range(121)]
    for x in res:
        if x["metodo"] == "Theis" and r:
            ax.semilogx(tt, [descenso_theis(q, x["T_m2_d"], x["S"], r, t / 1440) for t in tt], "-", color="#0071e3", label="Theis")
        if x["metodo"] == "Cooper-Jacob":
            m = x["pendiente_m_por_ciclo"]
            ax.semilogx(tt, [max(0.0, m * math.log10(t / x["t0_min"])) for t in tt], "--", color="#86868b", label="Cooper-Jacob")
    ax.set_xlabel("Tiempo desde el inicio del bombeo (min)")
    ax.set_ylabel("Descenso (m)")
    ax.invert_yaxis()
    ax.grid(True, which="both", lw=0.3, alpha=0.5)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ruta)
    return True


def salida_utf8():
    """Escribe siempre en UTF-8, también cuando Windows redirige la salida con otra codificación."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    salida_utf8()
    p = argparse.ArgumentParser(description="Interpretación de ensayos de bombeo (Cooper-Jacob, Theis, recuperación).")
    p.add_argument("csv", help="CSV con columnas t_min y s_m")
    p.add_argument("--q", type=float, required=True, help="Caudal de bombeo en L/s")
    p.add_argument("--r", type=float, default=None, help="Distancia al pozo de bombeo en m (o radio efectivo si es el propio pozo)")
    p.add_argument("--b", type=float, default=None, help="Espesor saturado en m, para obtener K")
    p.add_argument("--metodo", choices=["ambos", "cooper-jacob", "theis"], default="ambos")
    p.add_argument("--tmin", type=float, default=None, help="Inicio del tramo de Cooper-Jacob, en minutos")
    p.add_argument("--tmax", type=float, default=None, help="Fin del tramo de Cooper-Jacob, en minutos")
    p.add_argument("--pozo-bombeo", action="store_true", help="Los datos son del propio pozo de bombeo")
    p.add_argument("--recuperacion", action="store_true", help="Los datos son de recuperación (descenso residual)")
    p.add_argument("--tp", type=float, default=None, help="Duración del bombeo en minutos (para recuperación)")
    p.add_argument("--grafico", default=None, help="Ruta de un PNG para el gráfico (requiere matplotlib)")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    filas, delim = leer_csv(a.csv)
    ct, cs = columna(filas, ALIAS_T), columna(filas, ALIAS_S)
    if not ct or not cs:
        raise SystemExit("No encuentro las columnas. Se esperan t_min y s_m (o tiempo_min y descenso_m).")
    datos = [(numero(f[ct], delim), numero(f[cs], delim)) for f in filas]
    datos = sorted((t, s) for t, s in datos if t is not None and s is not None)
    if len(datos) < 3:
        raise SystemExit("Se necesitan al menos 3 lecturas válidas.")
    t_min = [d[0] for d in datos]
    s = [d[1] for d in datos]
    t_d = [t / 1440.0 for t in t_min]
    q = a.q * 86.4  # L/s a m3/d

    res = []
    if a.recuperacion:
        if not a.tp:
            raise SystemExit("Para recuperación indica --tp (duración del bombeo en minutos).")
        x = recuperacion(t_d, s, q, a.tp / 1440.0)
        if x:
            res.append(x)
    else:
        cj = None
        if a.metodo in ("ambos", "cooper-jacob"):
            cj = cooper_jacob(t_d, s, q, a.r,
                              a.tmin / 1440.0 if a.tmin else None,
                              a.tmax / 1440.0 if a.tmax else None)
            if cj:
                res.append(cj)
        if a.metodo in ("ambos", "theis") and a.r:
            th = theis(t_d, s, q, a.r, (cj["T_m2_d"], cj["S"]) if cj else None)
            if th:
                res.append(th)
    if not res:
        raise SystemExit("No se pudo ajustar ningún método. Revisa que el descenso aumente con el tiempo y las unidades.")

    for x in res:
        x["T_m2_s"] = x["T_m2_d"] / 86400.0
        if a.b:
            x["K_m_d"] = x["T_m2_d"] / a.b
            x["K_m_s"] = x["K_m_d"] / 86400.0
    avisos = advertencias(res, a.r, a.pozo_bombeo, len([1 for d in s if d > 0]))

    diag = None if a.recuperacion else diagnostico(t_d, s, q)
    if a.grafico and not a.recuperacion:
        graficar(a.grafico, t_min, s, res, q, a.r)
    elif a.grafico:
        print("Aviso: el gráfico solo está disponible para el ensayo de bombeo, no para la recuperación.", file=sys.stderr)

    if a.json:
        print(json.dumps({"entrada": {"archivo": a.csv, "Q_L_s": a.q, "Q_m3_d": q, "r_m": a.r, "b_m": a.b,
                                      "lecturas": len(datos)}, "resultados": res, "diagnostico": diag, "advertencias": avisos},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"# Ensayo de bombeo: {a.csv}\n")
    print(f"- Caudal: {a.q:g} L/s = {q:.4g} m³/d")
    print(f"- Distancia r: {fmt(a.r)} m · Espesor b: {fmt(a.b)} m · Lecturas: {len(datos)}")
    print(f"- Tiempo: {t_min[0]:g} a {t_min[-1]:g} min · Descenso máximo: {max(s):.3g} m\n")
    print("| Método | T (m²/d) | T (m²/s) | S (–) | K (m/d) | K (m/s) | R² | Puntos |")
    print("|---|---|---|---|---|---|---|---|")
    for x in res:
        print(f"| {x['metodo']} | {fmt(x['T_m2_d'])} | {fmt(x['T_m2_s'])} | {fmt(x.get('S'))} | "
              f"{fmt(x.get('K_m_d'))} | {fmt(x.get('K_m_s'))} | {fmt(x.get('r2'), 4)} | {x['puntos_usados']} |")
    for x in res:
        if x["metodo"] == "Cooper-Jacob":
            print(f"\nCooper-Jacob: pendiente {fmt(x['pendiente_m_por_ciclo'])} m por ciclo logarítmico, "
                  f"t₀ = {fmt(x['t0_min'])} min, tramo usado {fmt(x['t_desde_min'])} a {fmt(x['t_hasta_min'])} min"
                  + (f", u máximo {fmt(x['u_maximo'])}." if x.get("u_maximo") is not None else "."))
        if x["metodo"] == "Theis":
            print(f"Theis: error cuadrático medio del ajuste {fmt(x['rmse_m'])} m.")
        if x["metodo"] == "Recuperación de Theis":
            print(f"\nRecuperación: tramo usado t/t' entre {fmt(x['tt_desde'])} y {fmt(x['tt_hasta'])} "
                  f"({x['puntos_usados']} lecturas, las más cercanas al final de la recuperación).")
            print(f"Pendiente {fmt(x['pendiente_m_por_ciclo'])} m por ciclo de t/t'. "
                  f"Descenso residual extrapolado en t/t' = 1: {fmt(x['descenso_residual_en_t_t1'])} m "
                  "(si se aleja de cero, hay bordes o recarga).")
    if diag:
        print("\n## Diagnóstico\n")
        print(f"- Derivada del descenso, ds/d(ln t): {fmt(diag['derivada_tramo_medio_m'])} m en el tramo medio "
              f"y {fmt(diag['derivada_tramo_final_m'])} m en el tramo final.")
        if diag["T_derivada_m2_d"]:
            print(f"- T estimada desde la derivada final: {fmt(diag['T_derivada_m2_d'])} m²/d.")
        print("- " + diag["lectura"])
    if avisos:
        print("\n## Advertencias\n")
        for av in avisos:
            print("- " + av)
    print("\nFórmulas: T = 2,303·Q/(4π·Δs); S = 2,25·T·t₀/r²; s = Q/(4πT)·W(u), u = r²S/(4Tt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
