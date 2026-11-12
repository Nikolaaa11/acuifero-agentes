/* Acuífero · lógica de la página (fichas, calculadoras, manual, recetas). El mapa vive en mapa.js. */
(function () {
  "use strict";
  var D = window.ACUIFERO, C = window.Calculos;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var local = /^(localhost|127\.|\[::1\]|$)/.test(location.hostname) || location.protocol === "file:";
  var SITIO = local ? D.sitio : location.origin;
  var GITHUB = "https://github.com/" + D.repo;
  var COLOR = { agente: "var(--c-agente)", skill: "var(--c-skill)", calc: "var(--c-calc)", app: "var(--c-app)", plataforma: "var(--c-plataforma)" };
  var PLATAFORMAS = [
    { id: "claude-code", nombre: "Claude Code", desc: "En la terminal o en la pestaña Code de la app de escritorio. Carga los agentes y las skills." },
    { id: "cowork", nombre: "Cowork y claude.ai", desc: "Se instala como plugin desde Personalizar. En Cowork cargan agentes y skills; en el chat de claude.ai, solo las skills." },
    { id: "hermes", nombre: "Hermes Agent", desc: "Las skills se copian a su carpeta y los agentes se instalan como skills con el mismo nombre." }
  ];

  var agentes = {}, skills = {}, etapas = {};
  D.agentes.forEach(function (a) { agentes[a.id] = a; });
  D.skills.forEach(function (s) { skills[s.id] = s; });
  D.etapas.forEach(function (e, i) { etapas[e.id] = { nombre: e.nombre, desc: e.desc, n: i + 1 }; });

  /* ---------- utilidades ---------- */
  function el(tag, attrs, hijos) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") e.className = attrs[k];
      else if (k === "text") e.textContent = attrs[k];
      else if (k === "html") e.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) e.setAttribute(k, attrs[k]);
    }
    (hijos || []).forEach(function (h) { if (h !== null && h !== undefined) e.appendChild(typeof h === "string" ? document.createTextNode(h) : h); });
    return e;
  }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

  var avisoT;
  function aviso(texto) {
    var a = $("#aviso");
    a.textContent = texto;
    a.classList.add("visible");
    clearTimeout(avisoT);
    avisoT = setTimeout(function () { a.classList.remove("visible"); }, 1900);
  }
  function copiar(texto, boton) {
    function listo() {
      aviso("Copiado");
      if (boton) { var antes = boton.textContent; boton.textContent = "Copiado"; setTimeout(function () { boton.textContent = antes; }, 1600); }
    }
    function respaldo() {
      var t = el("textarea", { style: "position:fixed;opacity:0;top:0;left:0" });
      t.value = texto; (document.querySelector("dialog[open]") || document.body).appendChild(t); t.select();
      try { document.execCommand("copy"); listo(); } catch (e) { aviso("No se pudo copiar: selecciona el texto a mano"); }
      t.remove();
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(texto).then(listo, respaldo);
    else respaldo();
  }
  /** Bloque de comando o de pedido, con botón Copiar. */
  function comando(texto, o) {
    o = o || {};
    var b = el("button", { type: "button", class: "copiar", text: "Copiar", "aria-label": "Copiar al portapapeles" });
    b.addEventListener("click", function () { copiar(texto, b); });
    return el("div", { class: "comando" + (o.texto ? " texto" : "") + (o.claro ? " claro" : "") }, [el("code", { text: texto, tabindex: "0" }), b]);
  }
  function guardar(clave, valor) { try { localStorage.setItem(clave, JSON.stringify(valor)); } catch (e) { /* sin almacenamiento */ } }
  function leer(clave, defecto) { try { var v = localStorage.getItem(clave); return v ? JSON.parse(v) : defecto; } catch (e) { return defecto; } }

  var SUP = { "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };
  /** Número con coma decimal y cifras significativas; notación científica cuando conviene. */
  function fmt(v, cifras) {
    cifras = cifras || 3;
    if (v === null || v === undefined || !isFinite(v)) return "—";
    if (v === 0) return "0";
    var a = Math.abs(v);
    if (a < 1e-3 || a >= 1e7) {
      var exp = Math.floor(Math.log10(a)), man = v / Math.pow(10, exp);
      var m = man.toFixed(cifras - 1);
      if (Math.abs(Number(m)) >= 10) { m = (Number(m) / 10).toFixed(cifras - 1); exp += 1; }
      return m.replace(".", ",") + " × 10" + String(exp).split("").map(function (c) { return SUP[c]; }).join("");
    }
    return new Intl.NumberFormat("es-CL", { maximumSignificantDigits: cifras }).format(v);
  }
  function num(v) { var n = Number(String(v).trim().replace(/\s/g, "").replace(",", ".")); return isFinite(n) ? n : NaN; }

  /* ---------- Markdown mínimo (para instrucciones y resultados) ---------- */
  function enLinea(t) {
    return esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }
  function markdown(txt) {
    var L = txt.replace(/\r/g, "").split("\n"), out = [], i = 0;
    function lista(base) {
      var ord = /^\s*\d+\.\s/.test(L[i]), h = "<" + (ord ? "ol" : "ul") + ">";
      while (i < L.length) {
        var m = L[i].match(/^(\s*)(?:[-*]|\d+\.)\s+(.*)$/);
        if (!m) { if (L[i].trim() === "" && i + 1 < L.length && /^\s*(?:[-*]|\d+\.)\s/.test(L[i + 1]) && L[i + 1].match(/^\s*/)[0].length >= base) { i++; continue; } break; }
        var sangria = m[1].length;
        if (sangria < base) break;
        if (sangria > base + 1) { h = h.replace(/<\/li>$/, "") + lista(sangria) + "</li>"; continue; }
        var cuerpo = m[2].replace(/^\[ \]\s*/, "☐ ").replace(/^\[x\]\s*/i, "☑ ");
        i++;
        while (i < L.length && L[i].trim() !== "" && !/^\s*(?:[-*]|\d+\.)\s/.test(L[i]) && !/^(#|```|\|)/.test(L[i].trim())) { cuerpo += " " + L[i].trim(); i++; }
        h += "<li>" + enLinea(cuerpo) + "</li>";
      }
      return h + "</" + (ord ? "ol" : "ul") + ">";
    }
    while (i < L.length) {
      var l = L[i];
      if (/^\s*```/.test(l)) {
        var cod = []; i++;
        while (i < L.length && !/^\s*```/.test(L[i])) { cod.push(L[i]); i++; }
        i++;
        var minimo = Math.min.apply(null, cod.filter(function (c) { return c.trim(); }).map(function (c) { return c.match(/^\s*/)[0].length; }).concat([99]));
        out.push("<pre><code>" + esc(cod.map(function (c) { return c.slice(minimo === 99 ? 0 : minimo); }).join("\n")) + "</code></pre>");
      } else if (/^#{1,4}\s/.test(l)) {
        var n = l.match(/^#+/)[0].length;
        out.push("<h" + (n <= 2 ? 4 : 5) + ">" + enLinea(l.replace(/^#+\s*/, "")) + "</h" + (n <= 2 ? 4 : 5) + ">");
        i++;
      } else if (/^\s*\|/.test(l)) {
        var filas = [];
        while (i < L.length && /^\s*\|/.test(L[i])) { filas.push(L[i].trim().replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); })); i++; }
        var cab = filas[0], resto = filas.slice(filas[1] && /^:?-+:?$/.test(filas[1][0]) ? 2 : 1);
        out.push('<div class="tabla-md"><table><thead><tr>' + cab.map(function (c) { return "<th>" + enLinea(c) + "</th>"; }).join("") + "</tr></thead><tbody>" +
          resto.map(function (f) { return "<tr>" + f.map(function (c) { return "<td>" + enLinea(c) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table></div>");
      } else if (/^\s*(?:[-*]|\d+\.)\s/.test(l)) {
        out.push(lista(l.match(/^\s*/)[0].length));
      } else if (l.trim() === "") {
        i++;
      } else {
        var p = [l.trim()]; i++;
        while (i < L.length && L[i].trim() !== "" && !/^\s*(#|```|\||[-*]\s|\d+\.\s)/.test(L[i])) { p.push(L[i].trim()); i++; }
        out.push("<p>" + enLinea(p.join(" ")) + "</p>");
      }
    }
    return out.join("");
  }

  /* ---------- cifras y textos generales ---------- */
  var totalPruebas = D.pruebas + (D.pruebas_web || 0);
  var N = { agentes: D.agentes.length, skills: D.skills.length, calculadoras: D.calculadoras.length, pruebas: totalPruebas };
  $$("[data-n]").forEach(function (e) { e.textContent = N[e.getAttribute("data-n")]; });
  $("#pie-version").textContent = "versión " + D.version;
  $("#pie-repo").href = GITHUB;
  var mini = $("#mini-etapas");
  D.etapas.forEach(function (e, i) { mini.appendChild(el("li", null, [el("span", { text: String(i + 1) }), e.nombre])); });

  /* ---------- agentes ---------- */
  var grillaA = $("#grilla-agentes"), filtros = $("#filtros-etapa"), etapaActiva = "";
  function tarjeta(item, tipo) {
    var arriba = tipo === "agente" ? etapas[item.etapa].n + " · " + etapas[item.etapa].nombre : (item.tipo === "calculo" ? "Calcula" : "Guía");
    var b = el("button", { type: "button", class: "pieza" + (tipo === "skill" ? " es-skill" : ""), "data-id": item.id, "aria-label": item.titulo + ": abrir ficha" }, [
      el("span", { class: "etapa" }, [el("i"), arriba]),
      el("h3", { text: item.titulo }),
      el("p", { text: item.resumen }),
      el("span", { class: "abajo" }, [el("code", { text: tipo === "skill" && item.comando ? item.comando : item.id }), el("span", { class: "mas", "aria-hidden": "true", text: "+" })])
    ]);
    b.addEventListener("click", function () { abrirFicha(item.id); });
    return b;
  }
  function pintarFiltros() {
    filtros.textContent = "";
    var todos = [{ id: "", nombre: "Todas", n: D.agentes.length }].concat(D.etapas.map(function (e) {
      return { id: e.id, nombre: e.nombre, n: D.agentes.filter(function (a) { return a.etapa === e.id; }).length };
    }));
    todos.forEach(function (t) {
      var b = el("button", { type: "button", "aria-pressed": String(t.id === etapaActiva) }, [t.nombre, el("small", { text: String(t.n) })]);
      b.addEventListener("click", function () {
        etapaActiva = t.id;
        pintarFiltros();
        $$(".pieza", grillaA).forEach(function (p) { p.hidden = !!etapaActiva && agentes[p.getAttribute("data-id")].etapa !== etapaActiva; });
      });
      filtros.appendChild(b);
    });
  }
  D.etapas.forEach(function (e) {
    D.agentes.filter(function (a) { return a.etapa === e.id; }).forEach(function (a) { grillaA.appendChild(tarjeta(a, "agente")); });
  });
  pintarFiltros();

  /* ---------- skills ---------- */
  var grillaS = $("#grilla-skills");
  D.skills.slice().sort(function (a, b) { return (a.tipo === "calculo" ? 0 : 1) - (b.tipo === "calculo" ? 0 : 1); })
    .forEach(function (s) { grillaS.appendChild(tarjeta(s, "skill")); });

  /* ---------- ficha ---------- */
  var ficha = $("#ficha"), fichaCuerpo = $("#ficha-cuerpo");
  function chip(texto, color, alClic) {
    var c = el(alClic ? "button" : "span", alClic ? { type: "button" } : null, [el("i", { style: "background:" + color }), texto]);
    if (alClic) c.addEventListener("click", alClic);
    return c;
  }
  function abrirFicha(id) {
    var a = agentes[id], s = skills[id], it = a || s;
    if (!it) return;
    var tipo = a ? "agente" : "skill";
    var partes = [];
    partes.push(el("span", { class: "tipo" }, [el("i", { style: "background:" + COLOR[tipo] }),
      a ? "Agente · etapa " + etapas[a.etapa].n + ", " + etapas[a.etapa].nombre.toLowerCase() : "Skill · " + (s.tipo === "calculo" ? "calcula con un script" : "guía y plantillas")]));
    partes.push(el("h2", { id: "ficha-titulo", text: it.titulo }));
    partes.push(el("code", { class: "id", text: it.id }));
    partes.push(el("p", { class: "resumen", text: it.resumen }));
    if (a) {
      partes.push(el("div", { class: "pares" }, [
        el("div", { class: "par" }, [el("h3", { text: "Qué necesita" }), el("p", { text: a.necesita })]),
        el("div", { class: "par" }, [el("h3", { text: "Qué entrega" }), el("p", { text: a.entrega })])
      ]));
    }
    if (s && s.comando) { partes.push(el("h3", { class: "sec", text: "Comando" })); partes.push(comando(s.comando)); }
    partes.push(el("h3", { class: "sec", text: "Pedido de ejemplo, listo para copiar" }));
    partes.push(comando(it.pedido, { texto: true, claro: true }));
    if (a && a.usa.length) {
      partes.push(el("h3", { class: "sec", text: "Skills que usa" }));
      partes.push(el("div", { class: "chips" }, a.usa.map(function (u) { return chip(skills[u].titulo, COLOR.skill, function () { abrirFicha(u); }); })));
    }
    if (a && a.apps.length) {
      partes.push(el("h3", { class: "sec", text: "Programas con los que trabaja" }));
      partes.push(el("div", { class: "chips" }, a.apps.map(function (p) { return chip(D.apps.filter(function (x) { return x.id === p; })[0].nombre, COLOR.app); })));
    }
    if (s) {
      var quien = D.agentes.filter(function (x) { return x.usa.indexOf(id) >= 0; });
      if (quien.length) {
        partes.push(el("h3", { class: "sec", text: "Agentes que la usan" }));
        partes.push(el("div", { class: "chips" }, quien.map(function (x) { return chip(x.titulo, COLOR.agente, function () { abrirFicha(x.id); }); })));
      }
      if (D.salidas && D.salidas[id]) {
        partes.push(el("h3", { class: "sec", text: "Resultado real con los datos de ejemplo" }));
        partes.push(el("div", { class: "md", html: markdown(D.salidas[id].replace(/^# .*\n/, "")) }));
      }
    }
    var botones = [];
    if (s && s.calculadora) botones.push(el("button", { type: "button", class: "btn", text: "Abrir la calculadora", onclick: function () { ficha.close(); irCalculadora(s.calculadora); } }));
    botones.push(el("button", { type: "button", class: "btn " + (botones.length ? "btn-gris" : ""), text: "Ver en el mapa", onclick: function () { ficha.close(); if (window.Acuifero.verEnMapa) window.Acuifero.verEnMapa(id); } }));
    if (s) botones.push(el("a", { class: "btn btn-gris", href: "descargas/skills/" + id + ".zip", download: "", text: "Descargar .zip" }));
    botones.push(el("a", { class: "btn btn-gris", href: GITHUB + "/blob/main/" + it.archivo, target: "_blank", rel: "noopener", text: "Ver en GitHub" }));
    partes.push(el("div", { class: "botones" }, botones));
    var copiaTodo = el("button", { type: "button", class: "btn btn-gris", style: "font-size:14px;padding:8px 15px;margin-top:12px", text: "Copiar instrucciones" });
    copiaTodo.addEventListener("click", function () { copiar(it.instrucciones, copiaTodo); });
    partes.push(el("details", { class: "todo" }, [
      el("summary", { text: "Leer las instrucciones completas " + (a ? "del agente" : "de la skill") }),
      el("p", { class: "nota", text: a ? "Es el texto que sigue el agente. También puedes copiarlo y pegarlo como instrucciones en cualquier chat." : "Es el texto que lee Claude cuando usa esta skill." }),
      copiaTodo,
      el("div", { class: "md", html: markdown(it.instrucciones) })
    ]));
    fichaCuerpo.textContent = "";
    partes.forEach(function (p) { fichaCuerpo.appendChild(p); });
    if (!ficha.open) ficha.showModal();
    $(".ficha-in", ficha).scrollTop = 0;
  }
  $("#ficha-cerrar").addEventListener("click", function () { ficha.close(); });
  ficha.addEventListener("click", function (e) { if (e.target === ficha) ficha.close(); });

  /* ---------- calculadoras ---------- */
  var pestanas = $("#calc-pestanas"), cuerpo = $("#calc-cuerpo"), calcActiva = leer("acuifero-calc", "unidades");
  function campo(rotulo, id, valor, o) {
    o = o || {};
    var entrada;
    if (o.opciones) {
      entrada = el("select", { id: "c-" + id }, o.opciones.map(function (op) { return el("option", { value: op, text: op, selected: op === valor ? "" : null }); }));
    } else {
      entrada = el("input", { id: "c-" + id, type: "text", inputmode: "decimal", value: valor, autocomplete: "off", spellcheck: "false" });
    }
    return el("label", { class: "campo" + (o.todo ? " todo" : "") }, [el("span", { text: rotulo }), entrada]);
  }
  function v(id) { var e = $("#c-" + id); return e.tagName === "SELECT" ? e.value : num(e.value); }
  function fila(dt, dd) { return [el("dt", { text: dt }), el("dd", { text: dd })]; }
  function salida(rotulo, principal, unidad, filas, notas, extra) {
    var s = el("div", { class: "salida" }, [
      el("p", { class: "rotulo-s", text: rotulo }),
      el("p", { class: "principal" }, [principal, unidad ? el("small", { text: unidad }) : null])
    ]);
    if (extra && extra.antes) s.appendChild(extra.antes);
    if (filas && filas.length) s.appendChild(el("dl", null, [].concat.apply([], filas)));
    if (extra && extra.grafico) s.appendChild(el("div", { class: "grafico" }, [extra.grafico]));
    (notas || []).forEach(function (n) { s.appendChild(el("p", { class: "nota-s" + (n.alerta ? " alerta" : ""), text: n.texto || n })); });
    return s;
  }
  function svg(vb, contenido) {
    var t = document.createElement("div");
    t.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + vb + '" role="img">' + contenido + "</svg>";
    return t.firstChild;
  }

  var CALC = {
    unidades: {
      titulo: "Conversor de unidades", que: "Conductividad hidráulica, caudal y transmisividad, sin errores de factor.", skill: "unidades-hidro",
      formula: "1 m/s = 86 400 m/d · 1 L/s = 86,4 m³/d",
      campos: function () {
        var m = Object.keys(C.UNIDADES), u = Object.keys(C.UNIDADES[m[0]]);
        return el("div", { class: "campos" }, [
          campo("Magnitud", "mag", m[0], { opciones: m, todo: true }),
          campo("Valor", "valor", "1e-5"), campo("De", "desde", u[0], { opciones: u }), campo("A", "hacia", "m/d", { opciones: u, todo: true })
        ]);
      },
      alCambiar: function (id) {
        if (id !== "c-mag") return;
        var u = Object.keys(C.UNIDADES[v("mag")]);
        ["desde", "hacia"].forEach(function (k, i) {
          var s = $("#c-" + k); s.textContent = "";
          u.forEach(function (op, j) { s.appendChild(el("option", { value: op, text: op, selected: j === i ? "" : null })); });
        });
      },
      calcular: function () {
        var val = v("valor"), d = v("desde"), h = v("hacia"), t = C.UNIDADES[v("mag")];
        var r = C.convertir(val, d, h);
        var filas = Object.keys(t).filter(function (u) { return u !== h; }).map(function (u) { return fila(u, fmt(C.convertir(val, d, u), 4)); });
        return salida(isFinite(val) ? fmt(val, 6) + " " + d + " equivale a" : "Escribe un valor", fmt(r, 4), h, filas,
          ["Acepta notación científica (1e-5) y coma decimal. El año es de 365,25 días; el galón es el de Estados Unidos."]);
      }
    },
    darcy: {
      titulo: "Ley de Darcy", que: "Caudal que pasa por una sección, velocidad real del agua y tiempo de viaje.", skill: null,
      formula: "Q = K · i · A\nv = K · i / nₑ\nt = L / v",
      campos: function () {
        return el("div", { class: "campos" }, [
          campo("Conductividad K (m/d)", "K", "10"), campo("Gradiente i (m/m)", "i", "0,005"),
          campo("Área de la sección A (m²)", "A", "2000"), campo("Porosidad eficaz nₑ (–)", "ne", "0,2"),
          campo("Distancia de viaje L (m)", "L", "500", { todo: true })
        ]);
      },
      calcular: function () {
        var r = C.darcy({ K: v("K"), i: v("i"), A: v("A"), ne: v("ne"), L: v("L") });
        var notas = ["La velocidad real supone flujo advectivo en medio poroso homogéneo. No considera dispersión ni retardo."];
        if (v("ne") > 0.5 || v("ne") <= 0) notas.unshift({ alerta: true, texto: "La porosidad eficaz debe estar entre 0 y 0,5." });
        return salida("Caudal por la sección", fmt(r.Q_m3_d), "m³/d", [
          fila("Caudal", fmt(r.Q_L_s) + " L/s"),
          fila("Velocidad de Darcy", fmt(r.v_darcy_m_d) + " m/d"),
          fila("Velocidad real del agua", fmt(r.v_real_m_d) + " m/d"),
          fila("Tiempo de viaje", fmt(r.t_viaje_d) + " d" + (isFinite(r.t_viaje_d) ? " (" + fmt(r.t_viaje_d / 365.25) + " años)" : ""))
        ], notas);
      }
    },
    theis: {
      titulo: "Descenso de Theis", que: "Cuánto baja el nivel a una distancia del pozo después de un tiempo de bombeo.", skill: "ensayo-bombeo",
      formula: "s = Q / (4πT) · W(u)\nu = r²S / (4Tt)",
      campos: function () {
        return el("div", { class: "campos" }, [
          campo("Caudal Q (L/s)", "Q", "12"), campo("Transmisividad T (m²/d)", "T", "450"),
          campo("Almacenamiento S (–)", "S", "2e-4"), campo("Distancia r (m)", "r", "35"),
          campo("Tiempo de bombeo t (min)", "t", "1440", { todo: true })
        ]);
      },
      calcular: function () {
        var p = { Q: v("Q"), T: v("T"), S: v("S"), r: v("r"), t: v("t") };
        var r = C.theis(p), g = null;
        if (isFinite(r.s_m) && p.t > 1) {
          var pts = C.curvaTheis(p, 1, Math.max(p.t, 10), 60), smax = pts[pts.length - 1][1] || 1, tmax = pts[pts.length - 1][0];
          var X = function (t) { return 46 + 330 * Math.log10(t) / Math.log10(tmax); }, Y = function (s) { return 14 + 132 * s / smax; };
          var d = pts.map(function (q, i) { return (i ? "L" : "M") + X(q[0]).toFixed(1) + " " + Y(q[1]).toFixed(1); }).join(" ");
          var ejes = "";
          for (var e = 0; Math.pow(10, e) <= tmax; e++) ejes += '<line x1="' + X(Math.pow(10, e)) + '" y1="14" x2="' + X(Math.pow(10, e)) + '" y2="146" stroke="#e8e8ed"/><text x="' + X(Math.pow(10, e)) + '" y="162" text-anchor="middle">' + fmt(Math.pow(10, e)) + "</text>";
          g = svg("0 0 390 180", ejes + '<line x1="46" y1="14" x2="376" y2="14" stroke="#d2d2d7"/><text x="40" y="18" text-anchor="end">0</text><text x="40" y="150" text-anchor="end">' + fmt(smax) +
            '</text><text x="211" y="177" text-anchor="middle">tiempo (min, escala logarítmica)</text><text x="12" y="84" text-anchor="middle" transform="rotate(-90 12 84)">descenso (m)</text><path d="' + d +
            '" fill="none" stroke="#0071e3" stroke-width="2.2" stroke-linecap="round"/><circle cx="' + X(tmax) + '" cy="' + Y(smax) + '" r="4.5" fill="#0071e3" stroke="#fff" stroke-width="1.5"/>');
          g.setAttribute("aria-label", "Curva de descenso contra tiempo");
        }
        var notas = [r.jacobValido ? "u es menor que 0,05: en este punto también vale la aproximación de Cooper-Jacob." : { alerta: true, texto: "u es mayor que 0,05: aquí no vale la aproximación de Cooper-Jacob." },
          "Supone acuífero confinado, homogéneo, de extensión infinita y pozo totalmente penetrante."];
        return salida("Descenso a " + fmt(p.r) + " m después de " + fmt(p.t) + " min", fmt(r.s_m), "m", [
          fila("u", fmt(r.u)), fila("W(u)", fmt(r.W, 4)), fila("Caudal", fmt(p.Q * 86.4, 4) + " m³/d")
        ], notas, { grafico: g });
      }
    },
    jacob: {
      titulo: "Cooper-Jacob", que: "Transmisividad y almacenamiento desde la recta del ensayo en papel semilogarítmico.", skill: "ensayo-bombeo",
      formula: "T = 2,303 · Q / (4π · Δs)\nS = 2,25 · T · t₀ / r²",
      campos: function () {
        return el("div", { class: "campos" }, [
          campo("Caudal Q (L/s)", "Q", "12"), campo("Pendiente Δs (m por ciclo)", "ds", "0,42"),
          campo("Tiempo t₀ con descenso cero (min)", "t0", "0,336"), campo("Distancia r (m)", "r", "35"),
          campo("Espesor saturado b (m), opcional", "b", "40", { todo: true })
        ]);
      },
      calcular: function () {
        var r = C.cooperJacob({ Q: v("Q"), ds: v("ds"), t0: v("t0"), r: v("r"), b: v("b") });
        var notas = ["Usa solo el tramo recto del ensayo, donde u es menor que 0,05."];
        if (isFinite(r.S) && (r.S < 1e-6 || r.S > 0.4)) notas.unshift({ alerta: true, texto: "S está fuera del rango físico habitual (10⁻⁶ a 0,4). Revisa r, t₀ y las unidades." });
        return salida("Transmisividad", fmt(r.T_m2_d), "m²/d", [
          fila("Transmisividad", fmt(r.T_m2_s) + " m²/s"), fila("Almacenamiento S", fmt(r.S)),
          fila("Conductividad K", fmt(r.K_m_d) + " m/d"), fila("Conductividad K", fmt(r.K_m_d / 86400) + " m/s")
        ], notas);
      }
    },
    ionico: {
      titulo: "Balance iónico", que: "Comprueba si un análisis de agua cierra, y qué tipo de agua es. Concentraciones en mg/L.", skill: "balance-ionico",
      formula: "error = 100 · (Σcat − Σan) / (Σcat + Σan), en meq/L",
      campos: function () {
        return el("div", { class: "campos cuatro" }, [
          el("p", { class: "grupo-titulo", text: "Cationes (mg/L)" }),
          campo("Ca", "Ca", "60,1"), campo("Mg", "Mg", "12,2"), campo("Na", "Na", "23,0"), campo("K", "K", "3,9"),
          el("p", { class: "grupo-titulo", text: "Aniones (mg/L)" }),
          campo("HCO₃", "HCO3", "219,7"), campo("Cl", "Cl", "21,3"), campo("SO₄", "SO4", "38,4"), campo("NO₃", "NO3", "3,1"),
          campo("CO₃", "CO3", "0")
        ]);
      },
      calcular: function () {
        var e = {};
        Object.keys(C.PESO_EQ).forEach(function (k) { e[k] = v(k) || 0; });
        var r = C.balanceIonico(e), m = r.meq;
        if (r.estado === "sin datos") return salida("Error de balance", "—", "", [], ["Escribe las concentraciones de los iones mayores."]);
        var izq = [["Na+K", m.Na + m.K], ["Ca", m.Ca], ["Mg", m.Mg]], der = [["Cl", m.Cl], ["HCO₃", m.HCO3 + m.CO3], ["SO₄", m.SO4]];
        var mx = Math.max.apply(null, izq.concat(der).map(function (q) { return q[1]; })) || 1, esc2 = 120 / mx, cx = 195;
        var poli = izq.map(function (q, i) { return (cx - q[1] * esc2).toFixed(1) + "," + (30 + i * 44); })
          .concat(der.slice().reverse().map(function (q, i) { return (cx + q[1] * esc2).toFixed(1) + "," + (30 + (2 - i) * 44); })).join(" ");
        var marcas = "";
        izq.forEach(function (q, i) { marcas += '<text x="' + (cx - 132) + '" y="' + (34 + i * 44) + '" text-anchor="end">' + q[0] + "</text>"; });
        der.forEach(function (q, i) { marcas += '<text x="' + (cx + 132) + '" y="' + (34 + i * 44) + '">' + q[0] + "</text>"; });
        var g = svg("0 0 390 160", '<line x1="' + cx + '" y1="14" x2="' + cx + '" y2="134" stroke="#d2d2d7"/><line x1="' + (cx - 120) + '" y1="134" x2="' + (cx + 120) + '" y2="134" stroke="#d2d2d7"/>' +
          '<polygon points="' + poli + '" fill="rgba(0,113,227,.14)" stroke="#0071e3" stroke-width="2" stroke-linejoin="round"/>' + marcas +
          '<text x="' + (cx - 120) + '" y="150" text-anchor="middle">' + fmt(mx) + '</text><text x="' + cx + '" y="150" text-anchor="middle">0</text><text x="' + (cx + 120) + '" y="150" text-anchor="middle">' + fmt(mx) + " meq/L</text>");
        g.setAttribute("aria-label", "Diagrama de Stiff de la muestra");
        var notas = [];
        if (r.error > 5) notas.push({ alerta: true, texto: "Sobran cationes: revisa alcalinidad o aniones no informados, o sodio sobreestimado." });
        if (r.error < -5) notas.push({ alerta: true, texto: "Sobran aniones: en aguas ácidas pueden faltar Fe, Al, Mn o NH₄." });
        notas.push("Aceptable hasta ±5 %; dudosa hasta ±10 %. El gráfico es el diagrama de Stiff de la muestra.");
        return salida("Error de balance iónico", (r.error > 0 ? "+" : "") + fmt(r.error), "%", [
          fila("Tipo de agua", r.tipo), fila("Σ cationes", fmt(r.sumaCationes, 4) + " meq/L"), fila("Σ aniones", fmt(r.sumaAniones, 4) + " meq/L"),
          fila("Sólidos disueltos calculados", fmt(r.sdtCalculado, 4) + " mg/L")
        ], notas, { antes: el("span", { class: "estado " + r.estado, text: r.estado.charAt(0).toUpperCase() + r.estado.slice(1) }), grafico: g });
      }
    },
    gradiente: {
      titulo: "Gradiente con tres pozos", que: "Gradiente hidráulico y dirección de flujo a partir de tres niveles. Coordenadas en metros.", skill: "mapa-piezometrico",
      formula: "Plano por tres puntos: h = a·x + b·y + c\ni = √(a² + b²) · el flujo va hacia −∇h",
      campos: function () {
        var c = [el("p", { class: "grupo-titulo", text: "Pozo A" }), campo("Este x (m)", "x1", "0"), campo("Norte y (m)", "y1", "0"), campo("Nivel h (m s. n. m.)", "h1", "105"),
          el("p", { class: "grupo-titulo", text: "Pozo B" }), campo("Este x (m)", "x2", "1000"), campo("Norte y (m)", "y2", "200"), campo("Nivel h (m s. n. m.)", "h2", "101,5"),
          el("p", { class: "grupo-titulo", text: "Pozo C" }), campo("Este x (m)", "x3", "300"), campo("Norte y (m)", "y3", "900"), campo("Nivel h (m s. n. m.)", "h3", "106,2")];
        return el("div", { class: "campos tres" }, c);
      },
      calcular: function () {
        var P = [1, 2, 3].map(function (k) { return { x: v("x" + k), y: v("y" + k), h: v("h" + k) }; });
        var r = C.tresPozos(P[0], P[1], P[2]);
        if (r.alineados || !isFinite(r.gradiente)) return salida("Gradiente hidráulico", "—", "", [], [{ alerta: true, texto: "Los tres pozos están alineados o falta un dato: no definen un plano." }]);
        var xs = P.map(function (p) { return p.x; }), ys = P.map(function (p) { return p.y; });
        var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
        var lado = Math.max(x1 - x0, y1 - y0) || 1, k = 130 / lado;
        var X = function (x) { return 40 + (x - x0) * k + (130 - (x1 - x0) * k) / 2; }, Y = function (y) { return 160 - (y - y0) * k - (130 - (y1 - y0) * k) / 2; };
        var az = r.azimut * Math.PI / 180, cx = X((x0 + x1) / 2), cy = Y((y0 + y1) / 2), dx = 46 * Math.sin(az), dy = -46 * Math.cos(az);
        var cont = '<polygon points="' + P.map(function (p) { return X(p.x).toFixed(1) + "," + Y(p.y).toFixed(1); }).join(" ") + '" fill="rgba(0,113,227,.07)" stroke="#d2d2d7"/>';
        cont += '<line x1="' + (cx - dx) + '" y1="' + (cy - dy) + '" x2="' + (cx + dx) + '" y2="' + (cy + dy) + '" stroke="#0071e3" stroke-width="2.6" stroke-linecap="round"/>';
        cont += '<polygon points="0,-8 6,5 -6,5" fill="#0071e3" transform="translate(' + (cx + dx) + " " + (cy + dy) + ") rotate(" + r.azimut + ')"/>';
        P.forEach(function (p, i) { cont += '<circle cx="' + X(p.x) + '" cy="' + Y(p.y) + '" r="4.5" fill="#1d1d1f"/><text x="' + (X(p.x) + 8) + '" y="' + (Y(p.y) - 7) + '">' + "ABC"[i] + " · " + fmt(p.h, 5) + "</text>"; });
        cont += '<g transform="translate(336 44)"><circle r="26" fill="#fff" stroke="#d2d2d7"/><text y="-31" text-anchor="middle">N</text><line x1="' + (-18 * Math.sin(az)) + '" y1="' + (18 * Math.cos(az)) + '" x2="' + (18 * Math.sin(az)) + '" y2="' + (-18 * Math.cos(az)) +
          '" stroke="#0071e3" stroke-width="2.4" stroke-linecap="round"/><polygon points="0,-7 5,4 -5,4" fill="#0071e3" transform="translate(' + (18 * Math.sin(az)) + " " + (-18 * Math.cos(az)) + ") rotate(" + r.azimut + ')"/></g>';
        var g = svg("0 0 390 190", cont);
        g.setAttribute("aria-label", "Ubicación de los tres pozos y dirección de flujo");
        return salida("Gradiente hidráulico", fmt(r.gradiente * 100), "%", [
          fila("Gradiente", fmt(r.gradiente) + " m/m"), fila("Dirección de flujo", fmt(r.azimut, 3) + "° desde el norte"), fila("Rumbo", r.rumbo)
        ], ["Tres pozos definen un plano: sirve como primera lectura en una zona pequeña y de un solo acuífero. Con más pozos usa la skill mapa-piezometrico."], { grafico: g });
      }
    },
    aba: {
      titulo: "Balance ácido-base", que: "Clasifica una muestra de roca o relave por su potencial de generar ácido. Resultados en kg CaCO₃/t.", skill: "balance-acido-base",
      formula: "PA = 31,25 · S (%)\nPNN = PN − PA\nrazón = PN / PA",
      campos: function () {
        return el("div", { class: "campos" }, [
          campo("Azufre como sulfuro (%)", "S", "2,2"), campo("Potencial de neutralización PN (kg CaCO₃/t)", "PN", "18"),
          campo("Razón bajo la cual genera", "rg", "1"), campo("Razón sobre la cual no genera", "rn", "2"),
          campo("Banda de incertidumbre del PNN (±)", "lim", "20", { todo: true })
        ]);
      },
      calcular: function () {
        var S = v("S"), PN = v("PN");
        if (!isFinite(S) || !isFinite(PN) || S < 0 || PN < 0) return salida("Clase del material", "—", "", [], [{ alerta: true, texto: "Escribe el azufre y el potencial de neutralización." }]);
        var r = C.balanceAcidoBase({ S: S, PN: PN, razonGen: v("rg"), razonNo: v("rn"), pnnLim: v("lim") });
        var mx = Math.max(r.PA, PN, 1), k = 250 / mx;
        var g = svg("0 0 390 110", '<text x="8" y="34">PA</text><rect x="46" y="20" width="' + (r.PA * k).toFixed(1) + '" height="22" rx="6" fill="#ff9500"/><text x="' + (52 + r.PA * k).toFixed(1) + '" y="35">' + fmt(r.PA) +
          '</text><text x="8" y="76">PN</text><rect x="46" y="62" width="' + (PN * k).toFixed(1) + '" height="22" rx="6" fill="#0071e3"/><text x="' + (52 + PN * k).toFixed(1) + '" y="77">' + fmt(PN) +
          '</text><text x="46" y="104">kg CaCO₃/t</text>');
        g.setAttribute("aria-label", "Potencial de acidez contra potencial de neutralización");
        var notas = [];
        if (r.porRazon !== r.porPnn) notas.push({ alerta: true, texto: "Los dos criterios no coinciden (razón: " + r.porRazon + "; potencial neto: " + r.porPnn + "). La muestra queda incierta: hace falta mineralogía o ensayo cinético." });
        if (S < 0.1) notas.push("Con menos de 0,1 % de azufre, la razón es muy sensible al error analítico.");
        notas.push("Los cortes por defecto son de uso común, no una norma. Usa los que exija la guía del proyecto.");
        var chip = { "generador": "rechazada", "incierto": "dudosa", "no generador": "aceptada" }[r.clase];
        return salida("Clase del material", r.clase.charAt(0).toUpperCase() + r.clase.slice(1), "", [
          fila("Potencial de acidez PA", fmt(r.PA) + " kg CaCO₃/t"), fila("Potencial neto PNN", (r.PNN > 0 ? "+" : "") + fmt(r.PNN) + " kg CaCO₃/t"),
          fila("Razón PN/PA", isFinite(r.razon) ? fmt(r.razon) : "sin PA"), fila("Según la razón", r.porRazon), fila("Según el potencial neto", r.porPnn)
        ], notas, { antes: el("span", { class: "estado " + chip, text: r.porRazon === r.porPnn ? "Ambos criterios coinciden" : "Criterios distintos" }), grafico: g });
      }
    },
    densidad: {
      titulo: "Carga equivalente de agua dulce", que: "Lleva un nivel medido en salmuera a carga de agua dulce, para comparar pozos de distinta densidad.", skill: "salares",
      formula: "h dulce = z + (ρ / ρ dulce) · (h − z)",
      campos: function () {
        return el("div", { class: "campos" }, [
          campo("Nivel medido h (m s. n. m.)", "h", "2300,50"), campo("Cota del tramo captado z (m s. n. m.)", "z", "2280,00"),
          campo("Densidad del agua del pozo (kg/m³)", "rho", "1205"), campo("Densidad del agua dulce (kg/m³)", "rd", "1000")
        ]);
      },
      calcular: function () {
        var h = v("h"), z = v("z"), rho = v("rho"), rd = v("rd");
        if (![h, z, rho, rd].every(isFinite)) return salida("Carga equivalente", "—", "", [], [{ alerta: true, texto: "Completa los cuatro valores." }]);
        var r = C.cargaEquivalente({ h: h, z: z, rho: rho, rhoDulce: rd });
        var dos = new Intl.NumberFormat("es-CL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        var col = Math.max(h - z, r.carga - z, 0.001), k = 110 / col;
        var g = svg("0 0 390 170", '<line x1="40" y1="140" x2="350" y2="140" stroke="#d2d2d7"/><text x="356" y="144">z</text>' +
          '<rect x="110" y="' + (140 - (h - z) * k).toFixed(1) + '" width="56" height="' + ((h - z) * k).toFixed(1) + '" rx="6" fill="rgba(0,113,227,.55)"/>' +
          '<rect x="224" y="' + (140 - (r.carga - z) * k).toFixed(1) + '" width="56" height="' + ((r.carga - z) * k).toFixed(1) + '" rx="6" fill="rgba(0,113,227,.18)" stroke="#0071e3"/>' +
          '<text x="138" y="158" text-anchor="middle">salmuera</text><text x="252" y="158" text-anchor="middle">agua dulce</text>' +
          '<text x="138" y="' + (132 - (h - z) * k).toFixed(1) + '" text-anchor="middle">' + dos.format(h) + '</text><text x="252" y="' + (132 - (r.carga - z) * k).toFixed(1) + '" text-anchor="middle">' + dos.format(r.carga) + "</text>");
        g.setAttribute("aria-label", "Columna de salmuera y columna equivalente de agua dulce");
        var notas = [];
        if (r.densidad < 950 || r.densidad > 1400) notas.push({ alerta: true, texto: "Densidad fuera del rango habitual (950 a 1400 kg/m³). Revisa la unidad." });
        if (z > h) notas.push({ alerta: true, texto: "La cota del tramo captado está sobre el nivel medido. Revisa los datos." });
        notas.push("Sirve para comparar niveles en horizontal y trazar la piezometría. Para gradientes verticales en agua de densidad variable hace falta otro tratamiento.");
        return salida("Carga equivalente de agua dulce", dos.format(r.carga), "m s. n. m.", [
          fila("Diferencia con el nivel medido", (r.diferencia >= 0 ? "+" : "") + dos.format(r.diferencia) + " m"),
          fila("Columna de agua sobre el tramo captado", dos.format(h - z) + " m"), fila("Densidad usada", fmt(r.densidad, 4) + " kg/m³")
        ], notas, { grafico: g });
      }
    }
  };

  function pintarCalc() {
    var def = CALC[calcActiva] || CALC.unidades;
    $$("button", pestanas).forEach(function (b) { b.setAttribute("aria-selected", String(b.getAttribute("data-id") === calcActiva)); });
    cuerpo.textContent = "";
    var izq = el("div", { role: "tabpanel" }, [el("h3", { text: def.titulo }), el("p", { class: "que", text: def.que }), def.campos(), el("pre", { class: "formula", text: def.formula })]);
    if (def.skill) izq.appendChild(el("button", { type: "button", class: "enlace-skill", text: "Ver la skill " + def.skill + " ›", onclick: function () { abrirFicha(def.skill); } }));
    var der = el("div", { "aria-live": "polite" });
    cuerpo.appendChild(izq); cuerpo.appendChild(der);
    function recalcular() { der.textContent = ""; try { der.appendChild(def.calcular()); } catch (e) { der.appendChild(salida("Resultado", "—", "", [], [{ alerta: true, texto: "Revisa los valores ingresados." }])); } }
    izq.addEventListener("input", function (e) { if (def.alCambiar) def.alCambiar(e.target.id); recalcular(); });
    izq.addEventListener("change", function (e) { if (def.alCambiar) def.alCambiar(e.target.id); recalcular(); });
    recalcular();
  }
  D.calculadoras.forEach(function (c) {
    var b = el("button", { type: "button", role: "tab", "data-id": c.id, text: c.nombre, title: c.desc });
    b.addEventListener("click", function () { calcActiva = c.id; guardar("acuifero-calc", c.id); pintarCalc(); });
    pestanas.appendChild(b);
  });
  if (!CALC[calcActiva]) calcActiva = "unidades";
  pintarCalc();
  function irCalculadora(id) {
    if (CALC[id]) { calcActiva = id; guardar("acuifero-calc", id); pintarCalc(); }
    $("#calculadoras").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---------- manual ---------- */
  var PS = function (opcion) { return "& ([scriptblock]::Create((irm " + SITIO + "/instalar.ps1))) " + opcion; };
  var SH = function (opcion) { return "curl -fsSL " + SITIO + "/instalar.sh | bash" + (opcion ? " -s -- " + opcion : ""); };
  function esperado(lineas) { return el("pre", { class: "esperado", "aria-label": "Lo que deberías ver" }, [lineas.join("\n")]); }
  function enlace(texto, url) { return el("a", { href: url, target: "_blank", rel: "noopener", text: texto }); }
  var PYTHON = { id: "python", titulo: "Comprueba que tienes Python", texto: "Los cálculos lo usan. Escribe esto en la terminal:", comandoDe: function (sis) { return sis === "windows" ? "python --version" : "python3 --version"; }, extra: function (sis) {
    return el("div", null, [
      el("p", { class: "donde" }, ["Si responde «Python 3» seguido de un número, ya lo tienes: pasa al siguiente paso."]),
      el("p", { class: "donde" }, sis === "windows"
        ? ["Si dice que no se reconoce o se abre la Microsoft Store, descárgalo gratis desde ", enlace("python.org", "https://www.python.org/downloads/"), ". Al instalarlo marca la casilla «Add python.exe to PATH». Después cierra PowerShell y ábrelo de nuevo."]
        : ["Si dice que no lo encuentra, descárgalo gratis desde ", enlace("python.org", "https://www.python.org/downloads/"), " y vuelve a abrir la Terminal."])
    ]);
  } };
  var PRUEBA = { id: "prueba", titulo: "Haz la primera prueba con datos de ejemplo", texto: "Pide esto en Claude. Debe darte una transmisividad cercana a 450 m²/d y un almacenamiento cercano a 2 × 10⁻⁴.",
    pedido: "Con la skill ensayo-bombeo interpreta el archivo ensayo-bombeo.csv que viene en la carpeta ejemplos de la skill. Caudal 12 L/s, pozo de observación a 35 m, espesor saturado 40 m." };

  function pasosDe(donde, sis) {
    var win = sis === "windows";
    if (donde === "code") return [
      { id: "tener", titulo: "Ten Claude instalado y con tu sesión iniciada", texto: "Sirve la app de escritorio de Claude (pestaña Code) o Claude Code en la terminal. Claude Code viene incluido en los planes de pago de Claude.",
        extra: function () { return el("p", { class: "donde" }, ["Si aún no la tienes, la app se descarga desde ", enlace("claude.ai/download", "https://claude.ai/download"), ". Ábrela e inicia sesión antes de seguir."]); } },
      win ? { id: "terminal", titulo: "Abre PowerShell", texto: "Menú Inicio, escribe «PowerShell» y ábrelo. No hace falta abrirlo como administrador. Ojo: tiene que ser PowerShell (ventana azul o negra con «PS» al inicio de la línea), no el Símbolo del sistema." }
          : { id: "terminal", titulo: "Abre la Terminal", texto: "En Mac: Cmd + Espacio y escribe «Terminal». En Linux, tu terminal de siempre." },
      PYTHON,
      { id: "instalar", titulo: "Pega esta línea y presiona Enter", texto: "Copia " + N.agentes + " agentes y " + N.skills + " skills a la carpeta .claude de tu usuario y comprueba sola que los cálculos funcionen. Si ya tenías algo con el mismo nombre, lo guarda antes en una carpeta de respaldo. No toca nada más.",
        comando: win ? "irm " + SITIO + "/instalar.ps1 | iex" : SH(""),
        extra: function () {
          return el("div", null, [
            el("p", { class: "donde", text: "En unos segundos deberías ver esto:" }),
            esperado(["Kit Acuifero " + D.version + " instalado.", "  " + N.agentes + " agentes en " + (win ? "C:\\Users\\tu-nombre\\.claude\\agents" : "/Users/tu-nombre/.claude/agents"),
              "  " + N.skills + " skills en " + (win ? "C:\\Users\\tu-nombre\\.claude\\skills" : "/Users/tu-nombre/.claude/skills"), "  Comprobación: los 13 cálculos funcionan (Python 3.12)."]),
            el("p", { class: "donde", text: "Si la línea de comprobación no aparece, falta Python: vuelve al paso anterior. Puedes correr el instalador las veces que quieras." }),
            el("details", null, [el("summary", { text: "¿Prefieres instalarlo como plugin?" }),
              el("p", { class: "donde", text: "Dentro de Claude Code escribe estos dos comandos, uno después del otro. En la app de escritorio también puedes usar el botón + junto al cuadro de mensaje y elegir «Add plugins»." }),
              comando("/plugin marketplace add " + D.repo), comando("/plugin install acuifero@acuifero-kit"),
              el("p", { class: "donde", text: "Como plugin, los agentes se llaman con el prefijo acuifero: (por ejemplo, acuifero:hidro-ensayos)." })]),
            el("details", null, [el("summary", { text: "¿Solo para un proyecto?" }),
              el("p", { class: "donde", text: "Abre la terminal dentro de la carpeta del proyecto y usa esta variante. Instala en la carpeta .claude de ese proyecto." }),
              comando(win ? PS("-Proyecto") : SH("--proyecto"))])
          ]);
        } },
      { id: "comprobar", titulo: "Mira el detalle de la comprobación", texto: "Opcional, pero útil la primera vez: corre cada cálculo con sus datos de ejemplo y te muestra el resultado uno por uno.",
        comando: win ? 'python "$HOME\\.claude\\skills\\guia-acuifero\\scripts\\comprobar.py"' : "python3 ~/.claude/skills/guia-acuifero/scripts/comprobar.py",
        extra: function () { return el("p", { class: "donde", text: "Tiene que terminar con «Todo funciona: los 13 cálculos dieron el resultado esperado»." }); } },
      { id: "reiniciar", titulo: "Cierra Claude del todo y vuelve a abrirlo", texto: "Claude lee los agentes y las skills al iniciar. Después pregunta qué tienes:", pedido: "¿Qué agentes y skills del kit Acuífero tengo disponibles? Usa la skill guia-acuifero." },
      PRUEBA,
      { id: "proyecto", titulo: "Prepara tu primer proyecto", texto: "Abre Claude en la carpeta del proyecto y pide esto. Crea las carpetas y el archivo de contexto que leen todos los agentes, con las reglas de confidencialidad.", pedido: "Usa la skill inicio-proyecto en esta carpeta." }
    ];
    if (donde === "cowork") return [
      { id: "abrir", titulo: "Abre Personalizar y entra a Plugins", texto: "En claude.ai o en la app de Claude: Personalizar (Customize) y luego Plugins. Los nombres de los menús pueden variar según el idioma de la app. Este camino no instala nada en el computador, así que sirve también en equipos de empresa." },
      { id: "agregar", titulo: "Agrega el repositorio del kit", texto: "Elige Agregar (Add), luego Agregar marketplace (Add marketplace), y escribe esto:", comando: D.repo },
      { id: "plugin", titulo: "Instala el plugin «acuifero»", texto: "Aparece dentro del marketplace acuifero-kit. En Cowork se cargan los agentes y las skills. En el chat de claude.ai se cargan solo las skills: los agentes funcionan en Cowork y en Claude Code." },
      { id: "zip", titulo: "Otra forma: sube solo las skills que quieras", texto: "En Configuración, Capacidades, activa «Ejecución de código y creación de archivos». Después, en Personalizar, Skills, sube el archivo .zip de cada skill.",
        extra: function () {
          return el("div", { class: "descargas" }, D.skills.map(function (s) { return el("a", { href: "descargas/skills/" + s.id + ".zip", download: "", text: s.titulo + " .zip" }); }));
        } },
      { id: "prueba", titulo: "Haz la primera prueba", texto: "Pide esto. Debe darte una transmisividad cercana a 450 m²/d.", pedido: "Con la skill ensayo-bombeo interpreta el archivo de ejemplo ensayo-bombeo.csv que trae la skill. Caudal 12 L/s, pozo de observación a 35 m, espesor saturado 40 m." }
    ];
    return [
      { id: "hermes", titulo: "Instala Hermes Agent", texto: "Descárgalo desde su sitio oficial. Tiene app de escritorio para Windows, Mac y Linux.",
        extra: function () { return el("p", { class: "donde" }, [enlace("hermes-agent.nousresearch.com", "https://hermes-agent.nousresearch.com/")]); } },
      { id: "modelo", titulo: "Conecta un modelo", texto: "En la terminal escribe este comando y elige el proveedor. Para usar Claude necesitas una clave de la API de Anthropic, o Claude Max con créditos de uso extra.", comando: "hermes model" },
      PYTHON,
      { id: "kit", titulo: "Instala el kit con la opción de Hermes", texto: "Instala todo en Claude y, además, copia las skills a la carpeta de Hermes. En Hermes los " + N.agentes + " agentes quedan como skills con el mismo nombre.",
        comando: win ? PS("-Hermes") : SH("--hermes"),
        extra: function () {
          return el("details", null, [el("summary", { text: "¿Ya usas Claude Code?" }),
            el("p", { class: "donde", text: "Según su documentación, Hermes puede traer tus conectores, skills e instrucciones desde Claude Code con este comando:" }),
            comando("hermes import-agent claude-code")]);
        } },
      { id: "prueba", titulo: "Haz la primera prueba", texto: "Abre el chat de Hermes y pregunta qué tienes.", comando: "hermes chat", pedido: "¿Qué skills del kit Acuífero tengo? Usa guia-acuifero y después interpreta el ensayo de ejemplo de la skill ensayo-bombeo: caudal 12 L/s, r = 35 m, espesor 40 m." }
    ];
  }

  var manual = leer("acuifero-manual", { donde: "code", sis: /Mac|Linux|iPhone|iPad|Android/.test(navigator.userAgent) && !/Windows/.test(navigator.userAgent) ? "mac" : "windows" });
  var hechos = leer("acuifero-pasos", {});
  function pintarManual() {
    $$("#manual-donde button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-v") === manual.donde)); });
    $$("#manual-sistema button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-v") === manual.sis)); });
    $("#manual-sistema-caja").hidden = manual.donde === "cowork";
    var lista = $("#manual-pasos"), pasos = pasosDe(manual.donde, manual.sis);
    lista.textContent = "";
    pasos.forEach(function (p, i) {
      var clave = manual.donde + (manual.donde === "cowork" ? "" : "-" + manual.sis) + "-" + p.id;
      var marca = el("button", { type: "button", class: "marca-paso", "aria-pressed": String(!!hechos[clave]), "aria-label": "Marcar el paso " + (i + 1) + " como hecho" }, [el("span", { text: String(i + 1) })]);
      var li = el("li", { class: "paso" + (hechos[clave] ? " hecho" : "") }, [marca, el("h4", { text: p.titulo }), el("p", { text: p.texto })]);
      if (p.comandoDe) li.appendChild(comando(p.comandoDe(manual.sis)));
      if (p.comando) li.appendChild(comando(p.comando));
      if (p.pedido) li.appendChild(comando(p.pedido, { texto: true, claro: true }));
      if (p.extra) li.appendChild(p.extra(manual.sis));
      marca.addEventListener("click", function () {
        hechos[clave] = !hechos[clave];
        guardar("acuifero-pasos", hechos);
        li.classList.toggle("hecho", !!hechos[clave]);
        marca.setAttribute("aria-pressed", String(!!hechos[clave]));
        avance(pasos);
      });
      lista.appendChild(li);
    });
    avance(pasos);
  }
  function avance(pasos) {
    var pre = manual.donde + (manual.donde === "cowork" ? "" : "-" + manual.sis) + "-";
    var n = pasos.filter(function (p) { return hechos[pre + p.id]; }).length;
    $("#avance-barra").style.width = (100 * n / pasos.length) + "%";
    $("#avance-texto").textContent = n === pasos.length ? "Listo: completaste los " + pasos.length + " pasos." : n + " de " + pasos.length + " pasos hechos";
  }
  $("#manual-donde").addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; manual.donde = b.getAttribute("data-v"); guardar("acuifero-manual", manual); pintarManual(); });
  $("#manual-sistema").addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; manual.sis = b.getAttribute("data-v"); guardar("acuifero-manual", manual); pintarManual(); });
  pintarManual();

  var quitar = $("#quitar-comandos");
  quitar.appendChild(el("p", { class: "etiqueta", text: "Windows (PowerShell)" }));
  quitar.appendChild(comando(PS("-Quitar")));
  quitar.appendChild(el("p", { class: "etiqueta", text: "Mac o Linux (Terminal)" }));
  quitar.appendChild(comando(SH("--quitar")));

  /* ---------- si algo falla ---------- */
  var ayuda = $("#lista-ayuda");
  [
    { q: "PowerShell dice que «irm» no se reconoce", r: ["Estás en el Símbolo del sistema, no en PowerShell. Cierra esa ventana, abre el menú Inicio, escribe «PowerShell» y pega la línea ahí."] },
    { q: "Windows dice que «python» no se reconoce, o se abre la Microsoft Store", r: ["Falta Python. Instálalo desde python.org y, en la primera pantalla del instalador, marca la casilla «Add python.exe to PATH». Cierra PowerShell, ábrelo de nuevo y vuelve a correr el instalador del kit: no pasa nada por correrlo dos veces."] },
    { q: "La descarga falla o el computador de la empresa bloquea el instalador", r: ["Instálalo a mano. Descarga el kit, descomprímelo y copia las carpetas «agents» y «skills» dentro de la carpeta .claude de tu usuario (C:\\Users\\tu-nombre\\.claude en Windows; /Users/tu-nombre/.claude en Mac). Si la carpeta .claude no existe, créala.",
      el("p", null, [el("a", { class: "btn btn-gris", style: "font-size:14px;padding:8px 15px", href: "descargas/acuifero-kit.zip", download: "", text: "Descargar el kit (.zip)" })]),
      "Si tu empresa no permite instalar nada, usa el camino «Cowork o claude.ai» de arriba: funciona desde la cuenta, sin tocar el equipo."] },
    { q: "Claude no muestra los agentes", r: ["Cierra Claude del todo (en Windows, también desde el ícono junto al reloj) y ábrelo otra vez. Después pídele esto:", comando("Lista los agentes que tienes disponibles cuyo nombre empieza con hidro- o geo-.", { texto: true, claro: true }),
      "Si no aparecen, revisa que existan archivos dentro de la carpeta .claude\\agents de tu usuario. Si la carpeta está vacía, corre de nuevo el instalador."] },
    { q: "Un cálculo da error o un resultado raro", r: ["Corre la comprobación. Te dice cuál de los 13 cálculos falla y por qué.", "Windows:", comando('python "$HOME\\.claude\\skills\\guia-acuifero\\scripts\\comprobar.py"'),
      "Mac o Linux:", comando("python3 ~/.claude/skills/guia-acuifero/scripts/comprobar.py"), "Si todo sale bien ahí, el problema está en tu archivo: pídele a Claude que revise los encabezados y las unidades contra lo que pide la skill."] },
    { q: "Quiero dejar todo como estaba y partir de nuevo", r: ["Desinstala y vuelve a instalar. Lo que habías modificado queda guardado en la carpeta acuifero-respaldo.", "Windows:", comando(PS("-Quitar")), "Mac o Linux:", comando(SH("--quitar"))] }
  ].forEach(function (it) {
    var d = el("details", null, [el("summary", { text: it.q })]);
    it.r.forEach(function (x) { d.appendChild(typeof x === "string" ? el("p", { text: x }) : x); });
    ayuda.appendChild(d);
  });

  /* ---------- líneas de trabajo ---------- */
  var grillaL = $("#grilla-lineas");
  (D.lineas || []).forEach(function (l) {
    grillaL.appendChild(el("article", { class: "linea" }, [el("h4", { text: l.nombre }), el("p", { text: l.desc }),
      el("div", { class: "chips" }, l.agentes.map(function (id) {
        return el("button", { type: "button", onclick: function () { abrirFicha(id); } }, [el("i", { style: "background:" + COLOR.agente }), agentes[id].titulo]);
      }))]));
  });

  /* ---------- recetas ---------- */
  var recLista = $("#recetas-lista"), recCuerpo = $("#recetas-cuerpo"), recActiva = D.rutas[0].id;
  function pintarReceta() {
    var r = D.rutas.filter(function (x) { return x.id === recActiva; })[0];
    $$("button", recLista).forEach(function (b) { b.setAttribute("aria-selected", String(b.getAttribute("data-id") === recActiva)); });
    recCuerpo.textContent = "";
    recCuerpo.appendChild(el("div", { class: "cab" }, [el("h3", { text: r.nombre }),
      el("button", { type: "button", class: "btn btn-gris", style: "font-size:14px;padding:8px 15px", text: "Ver la ruta en el mapa", onclick: function () { if (window.Acuifero.rutaEnMapa) window.Acuifero.rutaEnMapa(r.id); } })]));
    r.pasos.forEach(function (id, i) {
      var it = agentes[id] || skills[id];
      var cab = el("h4", null, [el("button", { type: "button", class: "enlace-skill", style: "margin:0;font-size:17px;font-weight:600;color:var(--tinta)", text: it.titulo, onclick: function () { abrirFicha(id); } }), el("code", { text: (agentes[id] ? "agente " : "skill ") + id })]);
      recCuerpo.appendChild(el("div", { class: "receta-paso" }, [el("span", { class: "n", text: String(i + 1) }), cab, el("p", { text: it.resumen }), comando(it.pedido, { texto: true, claro: true })]));
    });
  }
  D.rutas.forEach(function (r) {
    var b = el("button", { type: "button", role: "tab", "data-id": r.id }, [r.nombre, el("small", { text: r.pasos.length + " pasos" })]);
    b.addEventListener("click", function () { recActiva = r.id; pintarReceta(); });
    recLista.appendChild(b);
  });
  pintarReceta();

  /* ---------- Hermes ---------- */
  function veredicto() {
    var m = $$("#hermes-marcas input:checked").map(function (i) { return i.value; });
    var t = "Con Claude te basta. Instala el kit en Claude y deja Hermes para más adelante.";
    if (m.indexOf("chat") >= 0 || m.indexOf("siempre") >= 0) t = "Hermes te sirve. Instala el kit en ambos: Claude para trabajar en tus carpetas y Hermes para pedirle cosas desde el chat o dejarlo trabajando solo.";
    else if (m.indexOf("modelos") >= 0) t = "Hermes te sirve para ahorrar: un modelo económico para las tareas simples, y Claude para las que exigen criterio.";
    $("#hermes-veredicto").textContent = t;
  }
  $("#hermes-marcas").addEventListener("change", veredicto);
  veredicto();

  /* ---------- barra, aparición y movimiento ---------- */
  var barra = $("#barra");
  function alDesplazar() { barra.classList.toggle("con-borde", window.scrollY > 8); }
  window.addEventListener("scroll", alDesplazar, { passive: true });
  alDesplazar();

  var quieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (quieto) { try { $("#corte-svg").pauseAnimations(); } catch (e) { /* sin SMIL */ } }
  $$(".bento .tarjeta, .reglas li, .preguntas details, .dos .tarjeta, .muestras .muestra").forEach(function (e) {
    var hermanos = Array.prototype.indexOf.call(e.parentNode.children, e);
    e.style.setProperty("--d", Math.min(hermanos, 5) * 70 + "ms");
  });
  if ("IntersectionObserver" in window && !quieto) {
    var ver = new IntersectionObserver(function (es) {
      es.forEach(function (x) { if (x.isIntersecting) { x.target.classList.add("visto"); ver.unobserve(x.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
    $$(".aparecer").forEach(function (e) { ver.observe(e); });
    var enlaces = $$("#enlaces a"), secciones = enlaces.map(function (a) { return $(a.getAttribute("href")); });
    var activo = new IntersectionObserver(function (es) {
      es.forEach(function (x) {
        if (!x.isIntersecting) return;
        enlaces.forEach(function (a) { a.classList.toggle("activo", a.getAttribute("href") === "#" + x.target.id); });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    secciones.forEach(function (s) { if (s) activo.observe(s); });
  } else {
    $$(".aparecer").forEach(function (e) { e.classList.add("visto"); });
  }

  window.Acuifero = {
    agentes: agentes, skills: skills, etapas: etapas, PLATAFORMAS: PLATAFORMAS, COLOR: COLOR,
    abrirFicha: abrirFicha, irCalculadora: irCalculadora, comando: comando, el: el, copiar: copiar
  };
})();
