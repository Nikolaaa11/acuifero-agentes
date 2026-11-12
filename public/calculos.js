/* Fórmulas de las calculadoras. Las mismas que usan los scripts de las skills.
   Funciona en el navegador (window.Calculos) y en Node (module.exports) para las pruebas. */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.Calculos = fabrica();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var EULER = 0.5772156649015329;
  var DIA = 86400, ANO = 365.25 * DIA, GAL = 0.003785411784, PIE = 0.3048;

  /** Función de pozo de Theis, W(u) = E1(u). */
  function wTheis(u) {
    if (!(u > 0)) return NaN;
    if (u < 1) {
      var suma = -EULER - Math.log(u), termino = u, signo = 1, n = 1;
      while (n < 200) {
        var aporte = (signo * termino) / n;
        suma += aporte;
        if (Math.abs(aporte) < 1e-17) break;
        n += 1;
        termino *= u / n;
        signo = -signo;
      }
      return suma;
    }
    if (u > 700) return 0;
    var b = u + 1, c = 1e300, d = 1 / b, h = d;
    for (var i = 1; i < 300; i++) {
      var an = -i * i;
      b += 2;
      d = 1 / (an * d + b);
      c = b + an / c;
      var delta = c * d;
      h *= delta;
      if (Math.abs(delta - 1) < 1e-15) break;
    }
    return h * Math.exp(-u);
  }

  var UNIDADES = {
    "Conductividad hidráulica": {
      "m/s": 1, "cm/s": 0.01, "m/d": 1 / DIA, "cm/d": 0.01 / DIA, "mm/d": 0.001 / DIA,
      "m/año": 1 / ANO, "ft/d": PIE / DIA, "gpd/ft²": GAL / DIA / (PIE * PIE)
    },
    "Caudal": {
      "L/s": 0.001, "m³/s": 1, "L/min": 0.001 / 60, "m³/h": 1 / 3600, "m³/d": 1 / DIA,
      "m³/año": 1 / ANO, "hm³/año": 1e6 / ANO, "gpm": GAL / 60
    },
    "Transmisividad": {
      "m²/d": 1 / DIA, "m²/s": 1, "m²/h": 1 / 3600, "cm²/s": 1e-4, "ft²/d": (PIE * PIE) / DIA, "gpd/ft": GAL / DIA / PIE
    }
  };

  function convertir(valor, desde, hacia) {
    for (var m in UNIDADES) {
      var t = UNIDADES[m];
      if (desde in t && hacia in t) return (valor * t[desde]) / t[hacia];
    }
    return NaN;
  }

  /** Ley de Darcy. K en m/d, gradiente adimensional, área en m², porosidad eficaz, distancia en m. */
  function darcy(p) {
    var q = p.K * p.i * p.A;
    var vd = p.K * p.i;
    var vr = p.ne > 0 ? vd / p.ne : NaN;
    return {
      Q_m3_d: q, Q_L_s: q / 86.4, v_darcy_m_d: vd, v_real_m_d: vr,
      t_viaje_d: p.L > 0 && vr > 0 ? p.L / vr : NaN
    };
  }

  /** Descenso de Theis. Q en L/s, T en m²/d, r en m, t en minutos. */
  function theis(p) {
    var q = p.Q * 86.4, t = p.t / 1440;
    var u = (p.r * p.r * p.S) / (4 * p.T * t);
    var w = wTheis(u);
    return { u: u, W: w, s_m: (q / (4 * Math.PI * p.T)) * w, jacobValido: u < 0.05 };
  }

  function curvaTheis(p, tMin, tMax, n) {
    var pts = [];
    for (var i = 0; i <= n; i++) {
      var t = tMin * Math.pow(tMax / tMin, i / n);
      pts.push([t, theis({ Q: p.Q, T: p.T, S: p.S, r: p.r, t: t }).s_m]);
    }
    return pts;
  }

  /** Cooper-Jacob. Q en L/s, ds = descenso por ciclo logarítmico (m), t0 en minutos, r en m. */
  function cooperJacob(p) {
    var q = p.Q * 86.4;
    var T = (2.302585 * q) / (4 * Math.PI * p.ds);
    var S = p.r > 0 && p.t0 > 0 ? (2.25 * T * (p.t0 / 1440)) / (p.r * p.r) : NaN;
    return { T_m2_d: T, T_m2_s: T / DIA, S: S, K_m_d: p.b > 0 ? T / p.b : NaN };
  }

  var PESO_EQ = { Ca: 20.039, Mg: 12.1525, Na: 22.9898, K: 39.0983, HCO3: 61.0168, CO3: 30.0044, Cl: 35.453, SO4: 48.0313, NO3: 62.0049 };
  var CATIONES = ["Ca", "Mg", "Na", "K"], ANIONES = ["HCO3", "CO3", "Cl", "SO4", "NO3"];

  function dominante(d) {
    var orden = Object.keys(d).sort(function (a, b) { return d[b] - d[a]; });
    return d[orden[0]] >= 50 ? orden[0] : orden[0] + "-" + orden[1];
  }

  /** Balance iónico. Entrada en mg/L. */
  function balanceIonico(mgL, limite) {
    limite = limite || 5;
    var meq = {};
    for (var ion in PESO_EQ) meq[ion] = (Number(mgL[ion]) || 0) / PESO_EQ[ion];
    var sc = 0, sa = 0;
    CATIONES.forEach(function (i) { sc += meq[i]; });
    ANIONES.forEach(function (i) { sa += meq[i]; });
    if (sc + sa === 0) return { meq: meq, sumaCationes: 0, sumaAniones: 0, error: NaN, estado: "sin datos", tipo: "—" };
    var err = (100 * (sc - sa)) / (sc + sa);
    var estado = Math.abs(err) <= limite ? "aceptada" : Math.abs(err) <= 2 * limite ? "dudosa" : "rechazada";
    var base = meq.HCO3 + meq.CO3 + meq.Cl + meq.SO4;
    var tipo = "—";
    if (sc > 0 && base > 0) {
      var an = { "bicarbonatada": (100 * (meq.HCO3 + meq.CO3)) / base, "clorurada": (100 * meq.Cl) / base, "sulfatada": (100 * meq.SO4) / base };
      var cat = { "cálcica": (100 * meq.Ca) / sc, "magnésica": (100 * meq.Mg) / sc, "sódica": (100 * (meq.Na + meq.K)) / sc };
      tipo = dominante(an) + " " + dominante(cat);
      tipo = tipo.charAt(0).toUpperCase() + tipo.slice(1);
    }
    var sdt = 0;
    for (var k in PESO_EQ) sdt += (k === "HCO3" ? 0.4917 : 1) * meq[k] * PESO_EQ[k];
    return { meq: meq, sumaCationes: sc, sumaAniones: sa, error: err, estado: estado, tipo: tipo, sdtCalculado: sdt };
  }

  var RUMBOS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"];
  function rumbo(az) { return isFinite(az) ? RUMBOS[Math.floor((az + 11.25) / 22.5) % 16] : "—"; }

  /** Gradiente y dirección de flujo con tres pozos. Cada pozo: {x, y, h} en metros. */
  function tresPozos(p1, p2, p3) {
    var x1 = p2.x - p1.x, y1 = p2.y - p1.y, h1 = p2.h - p1.h;
    var x2 = p3.x - p1.x, y2 = p3.y - p1.y, h2 = p3.h - p1.h;
    var det = x1 * y2 - x2 * y1;
    if (Math.abs(det) < 1e-9) return { gradiente: NaN, azimut: NaN, rumbo: "—", alineados: true };
    var a = (h1 * y2 - h2 * y1) / det, b = (x1 * h2 - x2 * h1) / det;
    var g = Math.sqrt(a * a + b * b);
    var az = g > 0 ? ((Math.atan2(-a, -b) * 180) / Math.PI + 360) % 360 : NaN;
    return { gradiente: g, azimut: az, rumbo: rumbo(az), alineados: false, a: a, b: b };
  }

  /** Balance ácido-base. S en % (azufre como sulfuro), PN en kg CaCO3/t. */
  function balanceAcidoBase(p) {
    var rg = p.razonGen || 1, rn = p.razonNo || 2, lim = p.pnnLim === undefined || isNaN(p.pnnLim) ? 20 : p.pnnLim;
    var pa = 31.25 * p.S, pnn = p.PN - pa, razon = pa > 0 ? p.PN / pa : Infinity;
    var porRazon = razon < rg ? "generador" : razon > rn ? "no generador" : "incierto";
    var porPnn = pnn < -lim ? "generador" : pnn > lim ? "no generador" : "incierto";
    return { PA: pa, PNN: pnn, razon: razon, porRazon: porRazon, porPnn: porPnn, clase: porRazon === porPnn ? porRazon : "incierto" };
  }

  /** Carga equivalente de agua dulce. Cotas en m; densidad en kg/m3 o en g/cm3. */
  function cargaEquivalente(p) {
    var rho = p.rho < 5 ? p.rho * 1000 : p.rho, rd = p.rhoDulce || 1000;
    var hf = p.z + (rho / rd) * (p.h - p.z);
    return { carga: hf, diferencia: hf - p.h, densidad: rho };
  }

  return {
    balanceAcidoBase: balanceAcidoBase, cargaEquivalente: cargaEquivalente,
    wTheis: wTheis, UNIDADES: UNIDADES, convertir: convertir, darcy: darcy, theis: theis, curvaTheis: curvaTheis,
    cooperJacob: cooperJacob, balanceIonico: balanceIonico, tresPozos: tresPozos, rumbo: rumbo, PESO_EQ: PESO_EQ
  };
});
