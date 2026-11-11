// Pruebas de las fórmulas de las calculadoras del sitio. Uso: node tools/probar_web.js
const path = require("path");
const C = require(path.join(__dirname, "..", "public", "calculos.js"));

let fallas = 0, total = 0;
function ok(nombre, cond, detalle) {
  total++;
  if (!cond) fallas++;
  console.log((cond ? "  bien  " : "  FALLA ") + nombre + (detalle !== undefined ? "  [" + detalle + "]" : ""));
}
const cerca = (a, b, rel) => Math.abs(a - b) <= rel * Math.abs(b);

console.log("Theis");
[[1e-4, 8.6332], [1e-2, 4.0379], [0.1, 1.8229], [1, 0.2194], [5, 0.0011483]].forEach(([u, w]) =>
  ok(`W(${u}) = ${w}`, cerca(C.wTheis(u), w, 2e-4), C.wTheis(u).toFixed(5)));
// Mismo caso que el ejemplo del kit: T = 450 m2/d, S = 2e-4, Q = 12 L/s, r = 35 m, t = 1440 min
const th = C.theis({ Q: 12, T: 450, S: 2e-4, r: 35, t: 1440 });
const esperado = (1036.8 / (4 * Math.PI * 450)) * C.wTheis((35 * 35 * 2e-4) / (4 * 450 * 1));
ok("descenso a 24 h coincide con la fórmula", cerca(th.s_m, esperado, 1e-12) && cerca(th.s_m, 1.52, 0.01), th.s_m.toFixed(4));
ok("u pequeño marca Cooper-Jacob válido", th.jacobValido === true && th.u < 0.001, th.u.toExponential(2));
ok("curva creciente en el tiempo", C.curvaTheis({ Q: 12, T: 450, S: 2e-4, r: 35 }, 1, 1440, 40).every((p, i, a) => i === 0 || p[1] > a[i - 1][1]));

console.log("Cooper-Jacob");
const cj = C.cooperJacob({ Q: 12, ds: 0.42, t0: 0.336, r: 35, b: 40 });
ok("T cerca de 452 m2/d con pendiente 0,42 m/ciclo", cerca(cj.T_m2_d, 452, 0.01), cj.T_m2_d.toFixed(1));
ok("S cerca de 1,94e-4", cerca(cj.S, 1.94e-4, 0.02), cj.S.toExponential(3));
ok("K = T/b", cerca(cj.K_m_d, cj.T_m2_d / 40, 1e-12));

console.log("Darcy");
const d = C.darcy({ K: 10, i: 0.005, A: 2000, ne: 0.2, L: 500 });
ok("Q = K·i·A = 100 m3/d", cerca(d.Q_m3_d, 100, 1e-12) && cerca(d.Q_L_s, 100 / 86.4, 1e-12), d.Q_m3_d);
ok("velocidad real = 0,25 m/d y viaje de 2000 d", cerca(d.v_real_m_d, 0.25, 1e-12) && cerca(d.t_viaje_d, 2000, 1e-12), d.t_viaje_d);

console.log("Unidades");
[[1e-5, "m/s", "m/d", 0.864], [12, "L/s", "m³/d", 1036.8], [450, "m²/d", "m²/s", 450 / 86400], [1, "gpm", "L/s", 0.0630902],
 [1, "hm³/año", "L/s", 31.6881], [1, "gpd/ft", "m²/d", 0.0124193], [1, "gpd/ft²", "m/d", 0.0407458]].forEach(([v, a, b, e]) =>
  ok(`${v} ${a} = ${e} ${b}`, cerca(C.convertir(v, a, b), e, 1e-5), C.convertir(v, a, b).toPrecision(6)));
ok("magnitudes distintas no se convierten", Number.isNaN(C.convertir(1, "m/s", "L/s")));

console.log("Balance iónico");
const b1 = C.balanceIonico({ Ca: 60.1, Mg: 12.2, Na: 23.0, K: 3.9, HCO3: 219.7, CO3: 0, Cl: 21.3, SO4: 38.4, NO3: 3.1 });
ok("PZ-01: 5,10 meq/L de cationes y error +0,5 %", cerca(b1.sumaCationes, 5.10, 0.01) && Math.abs(b1.error - 0.52) < 0.1, b1.error.toFixed(2));
ok("PZ-01: aceptada, bicarbonatada cálcica", b1.estado === "aceptada" && b1.tipo === "Bicarbonatada cálcica", b1.tipo);
const b5 = C.balanceIonico({ Ca: 100.2, Mg: 24.3, Na: 137.9, K: 7.8, HCO3: 183.1, CO3: 0, Cl: 141.8, SO4: 168.1, NO3: 0 });
ok("PZ-05: rechazada con +11,4 %", b5.estado === "rechazada" && Math.abs(b5.error - 11.38) < 0.1, b5.error.toFixed(2));
const b3 = C.balanceIonico({ Ca: 120.2, Mg: 60.8, Na: 1379.4, K: 78.2, HCO3: 183.1, CO3: 0, Cl: 2056.3, SO4: 528.3, NO3: 0 });
ok("PZ-03: clorurada sódica", b3.tipo === "Clorurada sódica", b3.tipo);
ok("sin datos no falla", C.balanceIonico({}).estado === "sin datos");

console.log("Tres pozos");
const g1 = C.tresPozos({ x: 0, y: 0, h: 105 }, { x: 1000, y: 0, h: 100 }, { x: 0, y: 1000, h: 105 });
ok("flujo hacia el este con gradiente 0,005", cerca(g1.gradiente, 0.005, 1e-12) && Math.abs(g1.azimut - 90) < 1e-9 && g1.rumbo === "E", g1.azimut);
const g2 = C.tresPozos({ x: 0, y: 0, h: 100 }, { x: 1000, y: 0, h: 100 }, { x: 0, y: 1000, h: 110 });
ok("flujo hacia el sur con gradiente 0,01", cerca(g2.gradiente, 0.01, 1e-12) && Math.abs(g2.azimut - 180) < 1e-9 && g2.rumbo === "S", g2.azimut);
ok("pozos alineados se detectan", C.tresPozos({ x: 0, y: 0, h: 1 }, { x: 1, y: 1, h: 2 }, { x: 2, y: 2, h: 3 }).alineados === true);

console.log(fallas ? `\n${fallas} de ${total} pruebas fallaron.` : `\nTodas las pruebas pasaron (${total}).`);
process.exit(fallas ? 1 : 0);
