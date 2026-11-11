/* Acuífero · mapa interactivo. Tres vistas, búsqueda, capas, rutas, acercamiento y pantalla completa. */
(function () {
  "use strict";
  var D = window.ACUIFERO, A = window.Acuifero;
  if (!D || !A) return;
  var NS = "http://www.w3.org/2000/svg";
  var caja = document.getElementById("mapa-caja"), lienzo = document.getElementById("mapa-lienzo");
  var svg = document.getElementById("mapa-svg"), panel = document.getElementById("mapa-panel");
  var COLOR = { agente: "#0071e3", skill: "#28a745", calc: "#ff9500", app: "#8e8e93", plataforma: "#1d1d1f" };
  var TIPO = { agente: "Agente", skill: "Skill", calc: "Calculadora", app: "Programa", plataforma: "Dónde se instala" };
  var TIPOS = { plataforma: "Dónde se instala", agente: "Agentes", skill: "Skills", calc: "Calculadoras", app: "Programas" };
  var ORDEN = ["plataforma", "agente", "skill", "calc", "app"];
  var ALTO = 32;

  function s(tag, attrs, texto) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  function plano(t) { return String(t).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }

  /* ---------- modelo ---------- */
  var nodos = [], N = {}, aristas = [], vecinos = {};
  function agregar(id, tipo, nombre, resumen, extra) {
    var n = { id: id, tipo: tipo, nombre: nombre, resumen: resumen, x: 0, y: 0, tx: 0, ty: 0, w: 100, oculto: false, extra: extra || {} };
    n.busca = plano(nombre + " " + id + " " + resumen);
    nodos.push(n); N[id] = n; vecinos[id] = [];
  }
  function unir(a, b, tipo) {
    if (!N[a] || !N[b]) return;
    aristas.push({ a: a, b: b, tipo: tipo });
    vecinos[a].push(b); vecinos[b].push(a);
  }
  A.PLATAFORMAS.forEach(function (p) { agregar("plat-" + p.id, "plataforma", p.nombre, p.desc); });
  D.etapas.forEach(function (e) {
    D.agentes.filter(function (a) { return a.etapa === e.id; }).forEach(function (a) { agregar(a.id, "agente", a.titulo, a.resumen, { etapa: a.etapa, pedido: a.pedido }); });
  });
  D.skills.forEach(function (k) { agregar(k.id, "skill", k.titulo, k.resumen, { pedido: k.pedido, calc: k.calculadora, calcula: k.tipo === "calculo" }); });
  D.calculadoras.forEach(function (c) { agregar("calc-" + c.id, "calc", c.nombre, c.desc + ". Funciona en esta página, sin instalar nada.", { calc: c.id }); });
  D.apps.forEach(function (p) { agregar("app-" + p.id, "app", p.nombre, p.desc); });
  D.agentes.forEach(function (a) {
    a.usa.forEach(function (k) { unir(a.id, k, "usa"); });
    a.apps.forEach(function (p) { unir(a.id, "app-" + p, "app"); });
  });
  D.skills.forEach(function (k) {
    if (k.calculadora) unir(k.id, "calc-" + k.calculadora, "calc");
    if (k.tipo === "calculo") unir(k.id, "app-python", "app");
  });
  unir("ensayo-bombeo", "calc-jacob", "calc");
  unir("hidro-conceptual", "calc-darcy", "calc");
  A.PLATAFORMAS.forEach(function (p) {
    D.agentes.forEach(function (a) { unir("plat-" + p.id, a.id, "instala"); });
    D.skills.forEach(function (k) { unir("plat-" + p.id, k.id, "instala"); });
  });
  function de(tipo) { return nodos.filter(function (n) { return n.tipo === tipo; }); }

  /* ---------- estado ---------- */
  var E = { vista: "flujo", sel: null, ruta: null, busca: "", capas: { plataforma: true, agente: true, skill: true, calc: true, app: true }, movil: false, orient: "v" };
  var vb = { x: 0, y: 0, w: 1100, h: 660 }, base = { x: 0, y: 0, w: 1100, h: 660 }, deco = [];

  /* ---------- dibujo ---------- */
  var gDeco = s("g", {}), gAristas = s("g", {}), gRuta = s("g", {}), gNodos = s("g", {});
  [gDeco, gAristas, gRuta, gNodos].forEach(function (g) { svg.appendChild(g); });
  var medir = document.createElement("canvas").getContext("2d");
  function medirNodos() {
    var fuente = getComputedStyle(document.body).fontFamily;
    medir.font = "500 13px " + fuente;
    nodos.forEach(function (n) {
      n.w = Math.ceil(medir.measureText(n.nombre).width) + 40;
      if (E.movil) n.w = Math.min(n.w, 170);
      var c = n.el.querySelector("rect.caja");
      c.setAttribute("x", -n.w / 2); c.setAttribute("width", n.w);
      n.el.querySelector("circle.punto").setAttribute("cx", -n.w / 2 + 15);
      n.el.querySelector("text.nombre").setAttribute("x", -n.w / 2 + 27);
      n.el.querySelector(".insignia").setAttribute("transform", "translate(" + (-n.w / 2 + 15) + " 0)");
    });
  }
  nodos.forEach(function (n) {
    var g = s("g", { class: "nodo " + n.tipo, tabindex: "0", role: "button", "aria-label": TIPO[n.tipo] + ": " + n.nombre });
    g.appendChild(s("rect", { class: "caja", y: -ALTO / 2, height: ALTO, rx: ALTO / 2 }));
    g.appendChild(s("circle", { class: "punto", cy: 0, r: 4.2, fill: n.tipo === "plataforma" ? "#fff" : COLOR[n.tipo] }));
    g.appendChild(s("text", { class: "nombre", y: 0, "dominant-baseline": "central" }, n.nombre));
    var ins = s("g", { class: "insignia", display: "none" });
    ins.appendChild(s("circle", { r: 9.5 }));
    ins.appendChild(s("text", { "text-anchor": "middle", "dominant-baseline": "central", y: 0.5 }, ""));
    g.appendChild(ins);
    g.addEventListener("click", function (ev) { if (arrastre.movio) return; ev.stopPropagation(); elegir(n.id); });
    g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); elegir(n.id); } });
    g.addEventListener("pointerenter", function () { if (!E.sel && !E.busca && !E.movil) resaltar(n.id); });
    g.addEventListener("pointerleave", function () { if (!E.sel && !E.busca && !E.movil) resaltar(null); });
    n.el = g; gNodos.appendChild(g);
  });
  aristas.forEach(function (a) { a.el = s("path", { class: "arista" }); gAristas.appendChild(a.el); });
  var caminoRuta = s("path", { class: "arista-ruta", display: "none" });
  gRuta.appendChild(caminoRuta);

  function trazo(p, q) {
    if (E.orient === "r") return "M" + p.x + " " + p.y + "L" + q.x + " " + q.y;
    if (E.orient === "h") { var mx = (p.x + q.x) / 2; return "M" + p.x + " " + p.y + "C" + mx + " " + p.y + " " + mx + " " + q.y + " " + q.x + " " + q.y; }
    var my = (p.y + q.y) / 2;
    return "M" + p.x + " " + p.y + "C" + p.x + " " + my + " " + q.x + " " + my + " " + q.x + " " + q.y;
  }
  function pintarPosiciones() {
    nodos.forEach(function (n) { n.el.setAttribute("transform", "translate(" + n.x.toFixed(1) + " " + n.y.toFixed(1) + ")"); });
    aristas.forEach(function (a) { a.el.setAttribute("d", trazo(N[a.a], N[a.b])); });
    if (E.ruta) {
      var pts = E.ruta.pasos.map(function (id) { return N[id]; }).filter(function (n) { return n && !n.oculto; });
      caminoRuta.setAttribute("d", pts.map(function (n, i) { return (i ? "L" : "M") + n.x.toFixed(1) + " " + n.y.toFixed(1); }).join(" "));
    }
    svg.setAttribute("viewBox", vb.x.toFixed(1) + " " + vb.y.toFixed(1) + " " + vb.w.toFixed(1) + " " + vb.h.toFixed(1));
  }
  function pintarDeco() {
    gDeco.textContent = "";
    deco.forEach(function (d) {
      if (d.t === "franja") gDeco.appendChild(s("rect", { class: "franja", x: d.x, y: d.y, width: d.w, height: d.h, rx: 16 }));
      else gDeco.appendChild(s("text", { class: "rotulo " + (d.cls || ""), x: d.x, y: d.y, "text-anchor": d.ancla || "start" }, d.texto));
    });
  }

  /* ---------- disposiciones ---------- */
  function repartir(lista, y, xa, xb, salto) {
    var n = lista.length, paso = (xb - xa) / n, ancho = Math.max.apply(null, lista.map(function (q) { return q.w; }));
    var alterna = salto && paso < ancho + 12;
    lista.forEach(function (q, i) { q.tx = xa + (i + 0.5) * paso; q.ty = y + (alterna && i % 2 ? salto : 0); });
    return alterna ? salto : 0;
  }
  function promedio(id, eje, tipos) {
    var v = vecinos[id].filter(function (o) { return tipos.indexOf(N[o].tipo) >= 0; });
    if (!v.length) return -1e9;
    return v.reduce(function (t, o) { return t + N[o][eje]; }, 0) / v.length;
  }
  function ordenar(lista, eje, tipos) {
    return lista.slice().sort(function (p, q) { return promedio(p.id, eje, tipos) - promedio(q.id, eje, tipos); });
  }

  function flujo() {
    var col = 152, izq = 20, ancho = col * D.etapas.length, der = izq + ancho;
    deco = [{ t: "rotulo", x: izq, y: 18, texto: "Dónde se instala" }];
    repartir(de("plataforma"), 46, izq + ancho / 2 - 280, izq + ancho / 2 + 280);
    var maximo = 0;
    D.etapas.forEach(function (e, i) {
      var cx = izq + col * (i + 0.5), ag = de("agente").filter(function (n) { return n.extra.etapa === e.id; });
      maximo = Math.max(maximo, ag.length);
      deco.push({ t: "rotulo", x: cx, y: 104, texto: (i + 1) + "  " + e.nombre, cls: "titulo", ancla: "middle" });
      ag.forEach(function (n, k) { n.tx = cx; n.ty = 142 + k * 42; });
    });
    D.etapas.forEach(function (e, i) { deco.unshift({ t: "franja", x: izq + col * i + 4, y: 116, w: col - 8, h: maximo * 42 + 10 }); });
    var y = 142 + maximo * 42 + 34;
    deco.push({ t: "rotulo", x: izq, y: y - 26, texto: "Skills" });
    y += repartir(ordenar(de("skill"), "tx", ["agente"]), y, izq, der, 40) + 76;
    deco.push({ t: "rotulo", x: izq, y: y - 26, texto: "Calculadoras de esta página" });
    y += repartir(ordenar(de("calc"), "tx", ["skill"]), y, izq, der, 38) + 76;
    deco.push({ t: "rotulo", x: izq, y: y - 26, texto: "Programas" });
    repartir(ordenar(de("app"), "tx", ["agente", "skill"]), y, izq, der, 38);
    nodos.forEach(function (n) { n.oculto = false; });
    E.orient = "v";
  }

  function tipos() {
    var xs = { plataforma: 110, agente: 330, skill: 560, calc: 790, app: 1000 }, pasos = { plataforma: 74, agente: 42, skill: 50, calc: 56, app: 52 }, cy = 340;
    deco = [];
    function columna(tipo, lista) {
      var p = pasos[tipo], y0 = cy - (lista.length - 1) * p / 2;
      lista.forEach(function (n, i) { n.tx = xs[tipo]; n.ty = y0 + i * p; n.oculto = false; });
      deco.push({ t: "rotulo", x: xs[tipo], y: 30, texto: TIPOS[tipo], cls: "titulo", ancla: "middle" });
    }
    columna("agente", de("agente"));
    columna("plataforma", de("plataforma"));
    columna("skill", ordenar(de("skill"), "ty", ["agente"]));
    columna("calc", ordenar(de("calc"), "ty", ["skill"]));
    columna("app", ordenar(de("app"), "ty", ["agente", "skill"]));
    E.orient = "h";
  }

  function foco() {
    var c = N[E.sel] || N["hidro-ensayos"];
    E.sel = c.id;
    var directos = vecinos[c.id].slice().sort(function (p, q) { return ORDEN.indexOf(N[p].tipo) - ORDEN.indexOf(N[q].tipo); });
    var segundos = [];
    directos.forEach(function (d) {
      if (N[d].tipo === "plataforma") return;
      vecinos[d].forEach(function (o) {
        if (o !== c.id && directos.indexOf(o) < 0 && segundos.indexOf(o) < 0 && N[o].tipo !== "plataforma") segundos.push(o);
      });
    });
    var a1 = directos.slice(0, 12), a2 = directos.slice(12).concat(segundos).slice(0, 22);
    nodos.forEach(function (n) { n.oculto = true; });
    c.tx = 555; c.ty = 330; c.oculto = false;
    function anillo(ids, rx, ry, giro) {
      ids.forEach(function (id, i) {
        var t = -Math.PI / 2 + giro + 2 * Math.PI * i / ids.length;
        N[id].tx = 555 + rx * Math.cos(t); N[id].ty = 330 + ry * Math.sin(t); N[id].oculto = false;
      });
    }
    anillo(a1, a2.length ? 290 : 360, a2.length ? 150 : 210, 0);
    anillo(a2, 520, 292, Math.PI / Math.max(a2.length, 1));
    nodos.forEach(function (n) { if (n.oculto) { n.tx = 555; n.ty = 330; } });
    deco = [{ t: "rotulo", x: 555, y: 16, texto: "Conexiones de «" + c.nombre + "»", cls: "titulo", ancla: "middle" }];
    E.orient = "r";
  }

  function vertical(grupos) {
    var y = 22, cols = [92, 268];
    deco = [];
    nodos.forEach(function (n) { n.oculto = true; n.tx = 180; n.ty = 60; });
    grupos.forEach(function (g) {
      if (!g.lista.length) return;
      deco.push({ t: "rotulo", x: 8, y: y, texto: g.titulo, cls: "titulo" });
      y += 28;
      g.lista.forEach(function (n, i) { n.tx = g.centro ? 180 : cols[i % 2]; n.ty = y + Math.floor(i / 2) * 42; n.oculto = false; });
      y += Math.ceil(g.lista.length / 2) * 42 + 16;
    });
    E.orient = "v";
  }
  function disponerMovil() {
    if (E.vista === "foco") {
      var c = N[E.sel] || N["hidro-ensayos"];
      E.sel = c.id;
      var dir = vecinos[c.id].map(function (id) { return N[id]; }).sort(function (p, q) { return ORDEN.indexOf(p.tipo) - ORDEN.indexOf(q.tipo); });
      vertical([{ titulo: "Elegido", lista: [c], centro: true }, { titulo: "Se conecta con", lista: dir }]);
      return;
    }
    var grupos = [{ titulo: "Dónde se instala", lista: de("plataforma") }];
    if (E.vista === "flujo") {
      D.etapas.forEach(function (e, i) { grupos.push({ titulo: (i + 1) + " · " + e.nombre, lista: de("agente").filter(function (n) { return n.extra.etapa === e.id; }) }); });
    } else grupos.push({ titulo: "Agentes", lista: de("agente") });
    grupos.push({ titulo: "Skills", lista: de("skill") }, { titulo: "Calculadoras de esta página", lista: de("calc") }, { titulo: "Programas", lista: de("app") });
    vertical(grupos);
  }

  function limites() {
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    nodos.forEach(function (n) {
      if (n.oculto) return;
      x0 = Math.min(x0, n.tx - n.w / 2); x1 = Math.max(x1, n.tx + n.w / 2);
      y0 = Math.min(y0, n.ty - ALTO / 2); y1 = Math.max(y1, n.ty + ALTO / 2);
    });
    deco.forEach(function (d) {
      if (d.t === "franja") { x0 = Math.min(x0, d.x); x1 = Math.max(x1, d.x + d.w); y0 = Math.min(y0, d.y); y1 = Math.max(y1, d.y + d.h); }
      else { x0 = Math.min(x0, d.x - (d.ancla === "middle" ? 90 : 0)); x1 = Math.max(x1, d.x + (d.ancla === "middle" ? 90 : 150)); y0 = Math.min(y0, d.y - 14); y1 = Math.max(y1, d.y + 4); }
    });
    var m = E.movil ? 8 : 26;
    return { x: x0 - m, y: y0 - m, w: x1 - x0 + 2 * m, h: y1 - y0 + 2 * m };
  }
  function encuadre() {
    var b = limites();
    if (E.movil) {
      b.x = 0; b.w = 360;
      svg.style.height = Math.round(b.h * lienzo.clientWidth / b.w) + "px";
      return b;
    }
    svg.style.height = "";
    var razon = lienzo.clientWidth / Math.max(lienzo.clientHeight, 1);
    if (b.w / b.h < razon) { var w = b.h * razon; b.x -= (w - b.w) / 2; b.w = w; }
    else { var h = b.w / razon; b.y -= (h - b.h) / 2; b.h = h; }
    return b;
  }

  var cuadro = 0;
  function animar(destinoVB, dur) {
    cancelAnimationFrame(cuadro);
    var quieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var desde = nodos.map(function (n) { return [n.x, n.y]; }), v0 = { x: vb.x, y: vb.y, w: vb.w, h: vb.h }, t0 = performance.now();
    if (!dur || quieto || document.hidden) {
      // Sin animación: se aplica de inmediato (también cuando la pestaña está en segundo plano)
      nodos.forEach(function (n) { n.x = n.tx; n.y = n.ty; });
      vb = { x: destinoVB.x, y: destinoVB.y, w: destinoVB.w, h: destinoVB.h };
      pintarPosiciones();
      return;
    }
    function paso(t) {
      var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 4);
      nodos.forEach(function (n, i) { n.x = desde[i][0] + (n.tx - desde[i][0]) * e; n.y = desde[i][1] + (n.ty - desde[i][1]) * e; });
      ["x", "y", "w", "h"].forEach(function (c) { vb[c] = v0[c] + (destinoVB[c] - v0[c]) * e; });
      pintarPosiciones();
      if (k < 1) cuadro = requestAnimationFrame(paso);
    }
    cuadro = requestAnimationFrame(paso);
  }
  function disponer(animado) {
    var eraMovil = E.movil;
    E.movil = window.matchMedia("(max-width: 820px)").matches;
    if (eraMovil !== E.movil || !nodos[0].medido) { medirNodos(); nodos[0].medido = true; }
    if (E.movil) disponerMovil();
    else if (E.vista === "tipos") tipos();
    else if (E.vista === "foco") foco();
    else flujo();
    pintarDeco();
    base = encuadre();
    refrescar();
    animar(base, animado ? 720 : 0);
  }

  /* ---------- estados visuales ---------- */
  function resaltar(id) {
    var cerca = id ? vecinos[id] : null;
    var enRuta = E.ruta ? E.ruta.pasos : null;
    nodos.forEach(function (n) {
      var c = n.el.classList, fuera = n.oculto || !E.capas[n.tipo];
      c.toggle("fuera", fuera);
      c.toggle("elegido", n.id === E.sel);
      c.toggle("vecino", !!cerca && cerca.indexOf(n.id) >= 0);
      var hallado = !!E.busca && n.busca.indexOf(E.busca) >= 0;
      c.toggle("hallado", hallado);
      var apagado = false;
      if (E.busca) apagado = !hallado;
      else if (id && E.vista !== "foco") apagado = n.id !== id && cerca.indexOf(n.id) < 0 && !(enRuta && enRuta.indexOf(n.id) >= 0);
      else if (!id && enRuta) apagado = enRuta.indexOf(n.id) < 0;
      c.toggle("apagado", apagado);
      var orden = enRuta ? enRuta.indexOf(n.id) : -1, ins = n.el.querySelector(".insignia");
      ins.setAttribute("display", orden >= 0 ? "inline" : "none");
      n.el.querySelector("circle.punto").setAttribute("display", orden >= 0 ? "none" : "inline");
      if (orden >= 0) ins.querySelector("text").textContent = String(orden + 1);
      n.el.setAttribute("tabindex", fuera ? "-1" : "0");
      n.el.setAttribute("aria-hidden", fuera ? "true" : "false");
    });
    aristas.forEach(function (a) {
      var toca = id && (a.a === id || a.b === id), c = a.el.classList;
      var fuera = N[a.a].oculto || N[a.b].oculto || !E.capas[N[a.a].tipo] || !E.capas[N[a.b].tipo] || (a.tipo === "instala" && !toca) || E.movil;
      c.toggle("fuera", !!fuera);
      c.toggle("viva", !!toca);
      c.toggle("apagada", !toca && ((!!id && E.vista !== "foco") || !!E.busca || !!E.ruta));
    });
    caminoRuta.setAttribute("display", E.ruta && !E.busca ? "inline" : "none");
  }
  function refrescar() { resaltar(E.sel); pintarPanel(); }

  /* ---------- panel ---------- */
  function punto(tipo) { var i = document.createElement("i"); i.style.background = COLOR[tipo]; return i; }
  function pintarPanel() {
    var el = A.el, n = N[E.sel];
    panel.textContent = "";
    panel.classList.toggle("con-algo", !!(n || E.ruta));
    if (n) {
      var cerrar = el("button", { type: "button", class: "panel-cerrar", "aria-label": "Quitar la selección", text: "×", onclick: function () { elegir(null); } });
      panel.appendChild(cerrar);
      panel.appendChild(el("span", { class: "tipo" }, [punto(n.tipo), TIPO[n.tipo] + (n.tipo === "agente" ? " · " + A.etapas[n.extra.etapa].nombre : "")]));
      panel.appendChild(el("h3", { text: n.nombre }));
      if (n.tipo === "agente" || n.tipo === "skill") panel.appendChild(el("code", { class: "id", text: n.id }));
      panel.appendChild(el("p", { text: n.resumen }));
      var grupos = {};
      vecinos[n.id].forEach(function (id) { (grupos[N[id].tipo] = grupos[N[id].tipo] || []).push(N[id]); });
      ORDEN.forEach(function (t) {
        if (!grupos[t]) return;
        var titulo = n.tipo === "plataforma" ? TIPOS[t] + " que carga" : t === "plataforma" ? "Dónde se instala" : n.tipo === "agente" && t === "skill" ? "Skills que usa" : n.tipo === "skill" && t === "agente" ? "Agentes que la usan" :
          t === "calc" ? "Calculadora equivalente" : t === "app" ? "Programas" : TIPOS[t];
        panel.appendChild(el("h4", { text: titulo }));
        panel.appendChild(el("div", { class: "chips" }, grupos[t].map(function (o) {
          return el("button", { type: "button", onclick: function () { elegir(o.id); } }, [punto(o.tipo), o.nombre]);
        })));
      });
      if (n.extra.pedido) { panel.appendChild(el("h4", { text: "Pedido de ejemplo" })); panel.appendChild(A.comando(n.extra.pedido, { texto: true, claro: true })); }
      var b = [];
      if (n.tipo === "agente" || n.tipo === "skill") b.push(el("button", { type: "button", class: "btn", text: "Ver ficha completa", onclick: function () { A.abrirFicha(n.id); } }));
      if (n.extra.calc) b.push(el("button", { type: "button", class: "btn " + (b.length ? "btn-gris" : ""), text: "Abrir calculadora", onclick: function () { salirCompleta(); A.irCalculadora(n.extra.calc); } }));
      if (E.vista !== "foco") b.push(el("button", { type: "button", class: "btn btn-gris", text: "Ver conexiones", onclick: function () { vista("foco"); } }));
      if (E.ruta) b.push(el("button", { type: "button", class: "btn btn-gris", text: "Volver a la ruta", onclick: function () { elegir(null); } }));
      panel.appendChild(el("div", { class: "botones" }, b));
      return;
    }
    if (E.ruta) {
      panel.appendChild(el("button", { type: "button", class: "panel-cerrar", "aria-label": "Salir de la ruta", text: "×", onclick: function () { ruta(""); } }));
      panel.appendChild(el("span", { class: "tipo" }, [punto("agente"), "Ruta de trabajo"]));
      panel.appendChild(el("h3", { text: E.ruta.nombre }));
      panel.appendChild(el("p", { text: "Sigue los pasos en orden. Toca uno para ver qué pedirle." }));
      panel.appendChild(el("ol", { class: "ruta" }, E.ruta.pasos.map(function (id) {
        return el("li", null, [el("button", { type: "button", onclick: function () { elegir(id); } }, [N[id].nombre, el("small", { text: TIPO[N[id].tipo] + " · " + id })])]);
      })));
      panel.appendChild(el("div", { class: "botones" }, [el("button", { type: "button", class: "btn btn-gris", text: "Salir de la ruta", onclick: function () { ruta(""); } })]));
      return;
    }
    panel.appendChild(el("h3", { text: "Cómo leer el mapa" }));
    panel.appendChild(el("ul", { class: "vacio" }, [
      el("li", null, [el("strong", { text: "Toca un nodo " }), "para ver qué hace, con qué se conecta y un pedido de ejemplo."]),
      el("li", null, [el("strong", { text: "Flujo " }), "ordena los agentes por etapa del proyecto. ", el("strong", { text: "Tipos " }), "los separa en columnas. ", el("strong", { text: "Conexiones " }), "pone un nodo al centro."]),
      el("li", null, [el("strong", { text: "Sigue una ruta " }), "para ver, numerados, los pasos de un encargo típico."]),
      el("li", null, [el("strong", { text: "Busca " }), "por nombre o por tema, y apaga las capas que no necesites."]),
      E.movil ? null : el("li", null, [el("strong", { text: "Arrastra " }), "para mover el mapa; usa + y − para acercar."])
    ]));
  }

  /* ---------- acciones ---------- */
  function elegir(id) {
    E.sel = id && E.sel === id && E.vista !== "foco" ? null : id;
    if (E.vista === "foco") { if (!E.sel) { vista("flujo"); return; } disponer(true); return; }
    refrescar();
  }
  function vista(v) {
    E.vista = v;
    Array.prototype.forEach.call(document.querySelectorAll("#mapa-vistas button"), function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-vista") === v)); });
    disponer(true);
  }
  function ruta(id) {
    E.ruta = D.rutas.filter(function (r) { return r.id === id; })[0] || null;
    document.getElementById("mapa-ruta").value = E.ruta ? id : "";
    E.sel = null;
    if (E.ruta && E.vista === "foco") { vista("flujo"); return; }
    if (E.vista === "foco") { vista("flujo"); return; }
    pintarPosiciones();
    refrescar();
  }
  function acercar(f, px, py) {
    var w = Math.min(base.w * 1.6, Math.max(base.w / 5, vb.w / f)), k = w / vb.w;
    var cx = px === undefined ? vb.x + vb.w / 2 : px, cy = py === undefined ? vb.y + vb.h / 2 : py;
    return { x: cx - (cx - vb.x) * k, y: cy - (cy - vb.y) * k, w: w, h: vb.h * k };
  }
  function salirCompleta() {
    if (!caja.classList.contains("completa")) return;
    caja.classList.remove("completa");
    document.documentElement.style.overflow = "";
    document.getElementById("mapa-pantalla").setAttribute("aria-pressed", "false");
    disponer(false);
  }

  document.getElementById("mapa-vistas").addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) vista(b.getAttribute("data-vista")); });
  var selRuta = document.getElementById("mapa-ruta");
  D.rutas.forEach(function (r) { var o = document.createElement("option"); o.value = r.id; o.textContent = r.nombre; selRuta.appendChild(o); });
  selRuta.addEventListener("change", function () { ruta(selRuta.value); });
  var buscar = document.getElementById("mapa-buscar");
  buscar.addEventListener("input", function () { E.busca = plano(buscar.value.trim()); refrescar(); });
  buscar.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || !E.busca) return;
    var hallado = nodos.filter(function (n) { return n.busca.indexOf(E.busca) >= 0 && E.capas[n.tipo]; })[0];
    if (hallado) { buscar.value = ""; E.busca = ""; if (hallado.oculto) E.vista = "flujo"; E.sel = null; disponer(false); elegir(hallado.id); }
  });
  var capas = document.getElementById("mapa-capas");
  ORDEN.forEach(function (t) {
    var b = document.createElement("button");
    b.type = "button"; b.setAttribute("aria-pressed", "true");
    b.appendChild(punto(t)); b.appendChild(document.createTextNode(TIPOS[t] + " "));
    var c = document.createElement("span"); c.className = "cuenta"; c.textContent = String(de(t).length); b.appendChild(c);
    b.addEventListener("click", function () { E.capas[t] = !E.capas[t]; b.setAttribute("aria-pressed", String(E.capas[t])); refrescar(); });
    capas.appendChild(b);
  });
  document.getElementById("mapa-mas").addEventListener("click", function () { animar(acercar(1.35), 260); });
  document.getElementById("mapa-menos").addEventListener("click", function () { animar(acercar(1 / 1.35), 260); });
  document.getElementById("mapa-ajustar").addEventListener("click", function () { animar(base, 420); });
  document.getElementById("mapa-pantalla").addEventListener("click", function () {
    if (caja.classList.contains("completa")) { salirCompleta(); return; }
    caja.classList.add("completa");
    document.documentElement.style.overflow = "hidden";
    this.setAttribute("aria-pressed", "true");
    disponer(false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || document.querySelector("dialog[open]")) return;
    if (caja.classList.contains("completa")) salirCompleta();
    else if (E.sel && caja.contains(document.activeElement)) elegir(null);
  });

  /* arrastre y acercamiento */
  var arrastre = { activo: false, movio: false };
  lienzo.addEventListener("pointerdown", function (e) {
    if (E.movil || e.button !== 0) return;
    arrastre = { activo: true, movio: false, x: e.clientX, y: e.clientY, vx: vb.x, vy: vb.y, id: e.pointerId };
  });
  lienzo.addEventListener("pointermove", function (e) {
    if (!arrastre.activo) return;
    var dx = e.clientX - arrastre.x, dy = e.clientY - arrastre.y;
    if (!arrastre.movio && Math.abs(dx) + Math.abs(dy) < 5) return;
    if (!arrastre.movio) { arrastre.movio = true; cancelAnimationFrame(cuadro); lienzo.classList.add("arrastrando"); try { lienzo.setPointerCapture(arrastre.id); } catch (err) { /* sin captura */ } }
    var k = vb.w / lienzo.clientWidth;
    vb.x = arrastre.vx - dx * k; vb.y = arrastre.vy - dy * k;
    pintarPosiciones();
  });
  function soltar() {
    if (!arrastre.activo) return;
    arrastre.activo = false;
    lienzo.classList.remove("arrastrando");
    setTimeout(function () { arrastre.movio = false; }, 0);
  }
  lienzo.addEventListener("pointerup", soltar);
  lienzo.addEventListener("pointercancel", soltar);
  lienzo.addEventListener("click", function () { if (!arrastre.movio && E.sel && E.vista !== "foco") elegir(null); });
  lienzo.addEventListener("wheel", function (e) {
    if (E.movil || !(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    var r = lienzo.getBoundingClientRect();
    var px = vb.x + (e.clientX - r.left) / r.width * vb.w, py = vb.y + (e.clientY - r.top) / r.height * vb.h;
    var d = acercar(Math.exp(-e.deltaY * 0.004), px, py);
    cancelAnimationFrame(cuadro);
    vb = d; pintarPosiciones();
  }, { passive: false });

  var espera;
  window.addEventListener("resize", function () { clearTimeout(espera); espera = setTimeout(function () { disponer(false); }, 160); });

  /* ---------- puertas para el resto de la página ---------- */
  A.verEnMapa = function (id) {
    document.getElementById("mapa").scrollIntoView({ behavior: "smooth", block: "start" });
    if (!N[id]) return;
    if (N[id].oculto) E.vista = "flujo";
    E.sel = null;
    if (E.vista === "foco") { E.sel = id; vista("foco"); } else { vista(E.vista); elegir(id); }
  };
  A.rutaEnMapa = function (id) {
    document.getElementById("mapa").scrollIntoView({ behavior: "smooth", block: "start" });
    if (E.vista !== "flujo") vista("flujo");
    ruta(id);
  };

  /* ---------- inicio ---------- */
  disponer(false);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { nodos[0].medido = false; disponer(false); });
})();
