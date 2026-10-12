"""The script that draws the car diagram from the data in the page. Plain
JavaScript, no libraries, nothing loaded from outside. Everything is on a grid
of cells: nodes sit on cells and cables run along cell lines, horizontal and
vertical only."""

SCRIPT = r"""
(function () {
  var holder = document.getElementById("car-data");
  var svg = document.getElementById("car-svg");
  if (!holder || !svg) return;
  var data = JSON.parse(holder.textContent);
  var NS = "http://www.w3.org/2000/svg";
  var G = data.grid;
  var nodes = {};
  data.nodes.forEach(function (node) { nodes[node.name] = node; });

  var world = document.getElementById("car-world");
  var view = { x: 0, y: 0, k: 1 };
  var MIN_K = 0.1, MAX_K = 4;

  // What the filter hides, by node name, and the switches.
  var options = { show: true, bundled: true, devices: true };
  var hidden = {};
  var selected = {};

  function visible(node) {
    return !hidden[node.name] && (node.kind === "box" || options.devices);
  }
  function shown() {
    return data.nodes.filter(visible);
  }

  function make(tag, attrs, parent) {
    var el = document.createElementNS(NS, tag);
    for (var name in attrs) el.setAttribute(name, attrs[name]);
    if (parent) parent.appendChild(el);
    return el;
  }

  // --- cables ---------------------------------------------------------------

  // Whether a node other than the link's own stands in the band between them.
  function blocked(a, b, horizontal) {
    return shown().some(function (n) {
      if (n === a || n === b) return false;
      if (horizontal) {
        return n.x >= Math.min(a.x + a.w, b.x + b.w) && n.x + n.w <= Math.max(a.x, b.x)
          && n.y < Math.max(a.y + a.h, b.y + b.h) && n.y + n.h > Math.min(a.y, b.y);
      }
      return n.y >= Math.min(a.y + a.h, b.y + b.h) && n.y + n.h <= Math.max(a.y, b.y)
        && n.x < Math.max(a.x + a.w, b.x + b.w) && n.x + n.w > Math.min(a.x, b.x);
    });
  }

  // Which sides a link uses: facing sides left and right when that way is
  // clear, else facing sides top and bottom when that is, else both top sides
  // (the cable goes over the top). Null when the nodes overlap both ways.
  function sides(a, b) {
    var gapX = Math.max(a.x - (b.x + b.w), b.x - (a.x + a.w));
    var gapY = Math.max(a.y - (b.y + b.h), b.y - (a.y + a.h));
    if (gapX >= 0 && !blocked(a, b, true)) return a.x < b.x ? ["right", "left"] : ["left", "right"];
    if (gapY >= 0 && !blocked(a, b, false)) return a.y < b.y ? ["bottom", "top"] : ["top", "bottom"];
    if (gapX >= 0 || gapY >= 0) return ["top", "top"];
    return null;
  }

  // Spread the links on one side of a node over distinct cells, ordered by
  // where they go, so two cables do not share a port.
  function ports(links) {
    var onSide = {};
    links.forEach(function (link, index) {
      var a = nodes[link.a], b = nodes[link.b];
      var s = sides(a, b);
      link.sides = s;
      if (!s) return;
      [[a, b, s[0], 0], [b, a, s[1], 1]].forEach(function (end) {
        var key = end[0].name + "|" + end[2];
        (onSide[key] = onSide[key] || []).push({ link: link, node: end[0], other: end[1], side: end[2], end: end[3] });
      });
    });
    Object.keys(onSide).forEach(function (key) {
      var list = onSide[key];
      var horizontal = list[0].side === "left" || list[0].side === "right";
      list.sort(function (p, q) {
        var pc = horizontal ? p.other.y + p.other.h / 2 : p.other.x + p.other.w / 2;
        var qc = horizontal ? q.other.y + q.other.h / 2 : q.other.x + q.other.w / 2;
        return pc - qc;
      });
      list.forEach(function (port, i) {
        var node = port.node;
        var length = horizontal ? node.h : node.w;
        var start = horizontal ? node.y : node.x;
        var at = Math.floor(length / 2 + (i - (list.length - 1) / 2) + 0.5);
        at = Math.max(1, Math.min(length - 1, at));
        port.link["at" + port.end] = start + at;
      });
    });
  }

  var overLanes = 0;
  function route(link) {
    var s = link.sides;
    if (!s) return null;
    var a = nodes[link.a], b = nodes[link.b];
    var p, q, mid;
    if (s[0] === "top" && s[1] === "top") {
      p = [link.at0, a.y];
      q = [link.at1, b.y];
      mid = Math.min(a.y, b.y) - 2 - (overLanes++ % 5);
      return [p, [p[0], mid], [q[0], mid], q];
    }
    if (s[0] === "right" || s[0] === "left") {
      p = [s[0] === "right" ? a.x + a.w : a.x, link.at0];
      q = [s[1] === "left" ? b.x : b.x + b.w, link.at1];
      mid = Math.round((p[0] + q[0]) / 2);
      return [p, [mid, p[1]], [mid, q[1]], q];
    }
    p = [link.at0, s[0] === "bottom" ? a.y + a.h : a.y];
    q = [link.at1, s[1] === "top" ? b.y : b.y + b.h];
    mid = Math.round((p[1] + q[1]) / 2);
    return [p, [p[0], mid], [q[0], mid], q];
  }

  // A cable's width follows its wires: not realistic, but a fat cable looks fat.
  function thickness(wires) {
    return Math.min(12, 2 + 1.1 * Math.sqrt(Math.max(wires, 1)));
  }

  // --- drawing --------------------------------------------------------------

  // The cables as drawn: one per pair of nodes with its cables bundled, or one
  // for each cable.
  var drawn = [];

  function items() {
    var links = data.links.filter(function (link) {
      return visible(nodes[link.a]) && visible(nodes[link.b]);
    });
    if (options.bundled) return links.map(function (link) {
      return { a: link.a, b: link.b, wires: link.wires, cables: link.cables };
    });
    var list = [];
    links.forEach(function (link) {
      link.cables.forEach(function (cable) {
        list.push({ a: link.a, b: link.b, wires: cable.wires, cables: [cable] });
      });
    });
    return list;
  }

  var cablesLayer, nodesLayer;
  var groups = {};
  var current = null;   // what is pointed at: a node, a cable's item or null

  // The grid and the nodes, once. Nodes are only moved afterwards, so a node
  // being dragged keeps its pointer.
  function build() {
    while (world.firstChild) world.removeChild(world.firstChild);
    var grid = make("rect", { x: -8000, y: -8000, width: 16000, height: 16000, fill: "url(#car-grid)" }, world);
    grid.setAttribute("class", "car-grid");
    cablesLayer = make("g", { "class": "car-cables" }, world);
    nodesLayer = make("g", {}, world);

    data.nodes.forEach(function (node) {
      var group = make("g", { transform: place(node) }, nodesLayer);
      groups[node.name] = group;
      group.setAttribute("class", "car-node car-" + node.kind);
      make("rect", { width: node.w * G, height: node.h * G, rx: 6 }, group);
      var label = make("text", { x: node.w * G / 2, y: node.kind === "box" ? node.h * G / 2 - 4 : node.h * G / 2 + 4,
                                 "text-anchor": "middle" }, group);
      label.setAttribute("class", "car-name");
      label.textContent = node.name;
      if (node.info) {
        var info = make("text", { x: node.w * G / 2, y: node.h * G / 2 + 16, "text-anchor": "middle" }, group);
        info.setAttribute("class", "car-info");
        info.textContent = node.info;
      }
      group.addEventListener("pointerenter", function () { focus(node); });
      group.addEventListener("pointerleave", function () { focus(null); });
      dragging(node, group);
    });
  }

  function place(node) {
    return "translate(" + node.x * G + "," + node.y * G + ")";
  }

  // The cables, again: when a node moves or a switch changes.
  function drawCables() {
    while (cablesLayer.firstChild) cablesLayer.removeChild(cablesLayer.firstChild);
    var list = items();
    ports(list);
    overLanes = 0;
    drawn = [];
    list.forEach(function (item) {
      var points = route(item);
      if (!points) return;
      var path = points.map(function (pt) { return (pt[0] * G) + "," + (pt[1] * G); }).join(" ");
      var line = make("polyline", { points: path, "stroke-width": thickness(item.wires) }, cablesLayer);
      line.setAttribute("class", "car-cable");
      // a wider line, drawn on top and invisible, so a thin cable is easy to point at
      var hit = make("polyline", { points: path, "stroke-width": Math.max(thickness(item.wires), 12) }, cablesLayer);
      hit.setAttribute("class", "car-hit");
      hit.addEventListener("pointerenter", function (event) { focus(item); tip(item, event); });
      hit.addEventListener("pointermove", function (event) { tip(item, event); });
      hit.addEventListener("pointerleave", function () { focus(null); tip(null); });
      drawn.push({ item: item, line: line });
    });
    svg.classList.toggle("hide-cables", !options.show);
    if (current && !current.kind) current = null;   // a cable of the old drawing is gone
    focus(current);
  }

  // --- selecting and moving nodes -------------------------------------------

  function paintSelection() {
    data.nodes.forEach(function (node) {
      groups[node.name].classList.toggle("selected", !!selected[node.name]);
    });
  }

  function overlaps(moving, dx, dy) {
    return shown().some(function (other) {
      if (selected[other.name]) return false;
      return moving.some(function (s) {
        var x = s.x + dx, y = s.y + dy;
        return x < other.x + other.w && other.x < x + s.node.w
          && y < other.y + other.h && other.y < y + s.node.h;
      });
    });
  }

  // A node, or every selected node when it is one of them, follows the pointer
  // one cell at a time and stays where it does not overlap another; the cables
  // follow. A click selects it; shift adds to or takes from the selection.
  function dragging(node, group) {
    var drag = null;
    group.addEventListener("pointerdown", function (event) {
      if (event.button !== 0 || panKey(event)) return;   // the view takes these
      event.stopPropagation();
      var was = !!selected[node.name];
      if (event.shiftKey) {
        if (was) delete selected[node.name]; else selected[node.name] = true;
        paintSelection();
        if (was) return;
      } else if (!was) {
        selected = {};
        selected[node.name] = true;
        paintSelection();
      }
      group.setPointerCapture(event.pointerId);
      drag = { id: event.pointerId, sx: event.clientX, sy: event.clientY, dx: 0, dy: 0, moved: false,
               collapse: was && !event.shiftKey,
               starts: Object.keys(selected).map(function (name) {
                 return { node: nodes[name], x: nodes[name].x, y: nodes[name].y };
               }) };
      group.classList.add("moving");
    });
    group.addEventListener("pointermove", function (event) {
      if (!drag || drag.id !== event.pointerId) return;
      var dx = Math.round((event.clientX - drag.sx) / view.k / G);
      var dy = Math.round((event.clientY - drag.sy) / view.k / G);
      if ((dx === drag.dx && dy === drag.dy) || overlaps(drag.starts, dx, dy)) return;
      drag.dx = dx;
      drag.dy = dy;
      drag.moved = true;
      drag.starts.forEach(function (s) {
        s.node.x = s.x + dx;
        s.node.y = s.y + dy;
        groups[s.node.name].setAttribute("transform", place(s.node));
      });
      drawCables();
    });
    function drop(event) {
      if (!drag || drag.id !== event.pointerId) return;
      group.classList.remove("moving");
      if (drag.moved) {
        save();
      } else if (drag.collapse) {
        selected = {};
        selected[node.name] = true;
        paintSelection();
      }
      drag = null;
    }
    group.addEventListener("pointerup", drop);
    group.addEventListener("pointercancel", drop);
  }

  // --- hover ----------------------------------------------------------------

  // What is pointed at: a node (its cables light up, or appear when cables are
  // switched off) or a cable (it lights up, and shows its name when cables are
  // shown). The rest dims.
  function focus(target) {
    current = target;
    svg.classList.toggle("focus", target !== null);
    drawn.forEach(function (entry) {
      var hot = target !== null && (target === entry.item || target.name === entry.item.a || target.name === entry.item.b);
      entry.line.classList.toggle("hot", hot);
    });
  }

  var tooltip = document.getElementById("car-tip");
  function tip(item, event) {
    if (!item || !options.show) { tooltip.hidden = true; return; }
    var lines = item.cables.slice(0, 8).map(function (cable) {
      return cable.name + " · " + cable.wires + (cable.wires === 1 ? " wire" : " wires");
    });
    if (item.cables.length > 8) lines.push("+" + (item.cables.length - 8) + " more");
    tooltip.textContent = lines.join("\n");
    tooltip.hidden = false;
    var box = svg.getBoundingClientRect();
    tooltip.style.left = (event.clientX - box.left + 14) + "px";
    tooltip.style.top = (event.clientY - box.top + 14) + "px";
  }

  // --- memory ---------------------------------------------------------------

  // What the page remembers in this browser: where the nodes were left, the
  // view and the switches. A different set of boxes and devices is a different
  // car and starts from the default layout.
  function hash(text) {
    var h = 0;
    for (var i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
    return (h >>> 0).toString(16);
  }
  var storeKey = "pharness-car:" + document.title + ":" +
    hash(data.nodes.map(function (n) { return n.name; }).sort().join("\n"));

  function whole(value) {
    return typeof value === "number" && isFinite(value) && Math.round(value) === value;
  }

  data.nodes.forEach(function (node) { node.dx = node.x; node.dy = node.y; });
  var restored = false;
  try {
    var saved = JSON.parse(localStorage.getItem(storeKey));
    if (saved) {
      data.nodes.forEach(function (node) {
        var at = saved.nodes && saved.nodes[node.name];
        if (at && whole(at[0]) && whole(at[1])) { node.x = at[0]; node.y = at[1]; }
      });
      if (saved.options) {
        options.show = saved.options.show !== false;
        options.bundled = saved.options.bundled !== false;
        options.devices = saved.options.devices !== false;
      }
      (saved.hidden || []).forEach(function (name) { if (nodes[name]) hidden[name] = true; });
      var v = saved.view;
      if (v && isFinite(v.x) && isFinite(v.y) && isFinite(v.k) && v.k >= MIN_K && v.k <= MAX_K) {
        view = { x: v.x, y: v.y, k: v.k };
        restored = true;
      }
    }
  } catch (e) { /* no memory here: the default layout */ }

  function save() {
    try {
      var moved = {};
      data.nodes.forEach(function (node) {
        if (node.x !== node.dx || node.y !== node.dy) moved[node.name] = [node.x, node.y];
      });
      localStorage.setItem(storeKey, JSON.stringify({ nodes: moved, view: view, options: options, hidden: Object.keys(hidden) }));
    } catch (e) { /* blocked or full: nothing is kept */ }
  }

  var saving = null;
  function saveSoon() {
    clearTimeout(saving);
    saving = setTimeout(save, 300);
  }

  // --- switches -------------------------------------------------------------

  function bind(id, name) {
    var input = document.getElementById(id);
    input.checked = options[name];
    input.addEventListener("change", function () {
      options[name] = input.checked;
      tip(null);
      drawCables();
      save();
    });
  }
  bind("car-show", "show");
  bind("car-bundled", "bundled");

  // --- the filter -----------------------------------------------------------

  var bar = document.getElementById("car-filter");
  var chips = {};

  function element(tag, parent, text, attrs) {
    var el = document.createElement(tag);
    if (text) el.textContent = text;
    for (var name in (attrs || {})) el.setAttribute(name, attrs[name]);
    parent.appendChild(el);
    return el;
  }

  function owned(box) {
    return data.nodes.filter(function (n) { return n.owner === box; }).map(function (n) { return n.name; });
  }

  // Show exactly these nodes, then fit the view to them.
  function only(names) {
    hidden = {};
    data.nodes.forEach(function (n) { if (names.indexOf(n.name) < 0) hidden[n.name] = true; });
    refresh();
    fit();
    save();
  }

  function neighbours(box) {
    var names = [box].concat(owned(box));
    data.links.forEach(function (link) {
      var other = link.a === box ? link.b : link.b === box ? link.a : null;
      if (other && nodes[other].kind === "box") names.push(other);
    });
    return names;
  }

  function buildFilter() {
    var boxes = data.nodes.filter(function (n) { return n.kind === "box"; });
    element("button", bar, "All").addEventListener("click", function () { only(data.nodes.map(function (n) { return n.name; })); });
    element("button", bar, "None").addEventListener("click", function () { only([]); });
    boxes.forEach(function (box) {
      var chip = element("button", bar, box.name, { "class": "chip", title: "Show or hide " + box.name + " and its devices" });
      chip.addEventListener("click", function () {
        var on = !!hidden[box.name];
        [box.name].concat(owned(box.name)).forEach(function (name) {
          if (on) delete hidden[name]; else hidden[name] = true;
        });
        refresh();
        save();
      });
      chips[box.name] = chip;
    });

    var label = element("label", bar, " Devices");
    var devices = element("input", label, "", { type: "checkbox" });
    label.insertBefore(devices, label.firstChild);
    devices.checked = options.devices;
    devices.addEventListener("change", function () {
      options.devices = devices.checked;
      refresh();
      save();
    });

    var focusOn = element("select", bar, "", { title: "Show one box and the boxes it is cabled to" });
    element("option", focusOn, "Box and neighbours…", { value: "" });
    boxes.forEach(function (box) { element("option", focusOn, box.name, { value: box.name }); });
    focusOn.addEventListener("change", function () {
      if (focusOn.value) only(neighbours(focusOn.value));
      focusOn.value = "";
    });

    var group = element("select", bar, "", { title: "Show only what a bus, link or chain touches" });
    element("option", group, "Bus, link or chain…", { value: "" });
    [["bus", "Buses"], ["link", "Links"], ["chain", "Chains"]].forEach(function (kind) {
      var found = data.groups.filter(function (g) { return g.kind === kind[0]; });
      if (!found.length) return;
      var section = element("optgroup", group, "", { label: kind[1] });
      found.forEach(function (g) { element("option", section, g.name, { value: kind[0] + ":" + g.name }); });
    });
    group.addEventListener("change", function () {
      var pick = data.groups.filter(function (g) { return group.value === g.kind + ":" + g.name; })[0];
      if (pick) only(pick.members);
      group.value = "";
    });
  }

  // Everything that follows from the filter: what is shown, the chips, the cables.
  function refresh() {
    data.nodes.forEach(function (node) {
      groups[node.name].style.display = visible(node) ? "" : "none";
      if (!visible(node)) delete selected[node.name];
    });
    paintSelection();
    Object.keys(chips).forEach(function (name) {
      chips[name].classList.toggle("off", !!hidden[name]);
    });
    tip(null);
    drawCables();
  }

  document.getElementById("car-reset").addEventListener("click", function () {
    data.nodes.forEach(function (node) {
      node.x = node.dx;
      node.y = node.dy;
      groups[node.name].setAttribute("transform", place(node));
    });
    drawCables();
    fit();
    save();
  });

  // --- zoom and pan ---------------------------------------------------------

  function apply(quiet) {
    world.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.k + ")");
    if (!quiet) saveSoon();
  }

  function zoomAt(px, py, factor) {
    var k = Math.max(MIN_K, Math.min(MAX_K, view.k * factor));
    factor = k / view.k;
    view.x = px - (px - view.x) * factor;
    view.y = py - (py - view.y) * factor;
    view.k = k;
    apply();
  }

  function fit(quiet) {
    var box = svg.getBoundingClientRect();
    if (!box.width || !box.height) return false;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    var list = shown();
    if (!list.length) return false;
    list.forEach(function (n) {
      minX = Math.min(minX, n.x); minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x + n.w); maxY = Math.max(maxY, n.y + n.h);
    });
    minY -= 7;   // room for cables that go over the top
    var width = (maxX - minX) * G, height = (maxY - minY) * G, margin = 24;
    var k = Math.min((box.width - 2 * margin) / width, (box.height - 2 * margin) / height, 1.5);
    view.k = Math.max(MIN_K, Math.min(MAX_K, k));
    view.x = (box.width - width * view.k) / 2 - minX * G * view.k;
    view.y = (box.height - height * view.k) / 2 - minY * G * view.k;
    apply(quiet);
    return true;
  }

  function local(event) {
    var box = svg.getBoundingClientRect();
    return [event.clientX - box.left, event.clientY - box.top];
  }

  svg.addEventListener("wheel", function (event) {
    event.preventDefault();
    var at = local(event);
    zoomAt(at[0], at[1], Math.exp(-event.deltaY * (event.deltaMode ? 0.05 : 0.0015)));
  }, { passive: false });

  // The view is dragged with the middle or right button, with Alt or Space
  // held, or with a finger; the left button on empty space selects.
  var spaceDown = false, overSvg = false;
  function panKey(event) {
    return event.button === 1 || event.button === 2 || event.altKey || spaceDown;
  }
  svg.addEventListener("contextmenu", function (event) { event.preventDefault(); });
  svg.addEventListener("pointerenter", function () { overSvg = true; });
  svg.addEventListener("pointerleave", function () { overSvg = false; });
  window.addEventListener("keydown", function (event) {
    if (event.key === " " && overSvg) { spaceDown = true; svg.classList.add("pannable"); event.preventDefault(); }
    if (event.key === "Escape") { selected = {}; paintSelection(); }
  });
  window.addEventListener("keyup", function (event) {
    if (event.key === " ") { spaceDown = false; svg.classList.remove("pannable"); }
  });

  var pointers = {};
  var pinch = null;
  var marquee = null;
  var box = make("rect", { "class": "car-marquee", display: "none" }, svg);

  svg.addEventListener("pointerdown", function (event) {
    svg.setPointerCapture(event.pointerId);
    if (!Object.keys(pointers).length && event.button === 0 && !panKey(event) && event.pointerType !== "touch") {
      var at = local(event);
      marquee = { id: event.pointerId, x0: at[0], y0: at[1], x1: at[0], y1: at[1], add: event.shiftKey };
      return;
    }
    pointers[event.pointerId] = local(event);
    pinch = null;
    svg.classList.add("grabbing");
  });

  function drawMarquee() {
    var x = Math.min(marquee.x0, marquee.x1), y = Math.min(marquee.y0, marquee.y1);
    box.setAttribute("x", x);
    box.setAttribute("y", y);
    box.setAttribute("width", Math.abs(marquee.x1 - marquee.x0));
    box.setAttribute("height", Math.abs(marquee.y1 - marquee.y0));
    box.setAttribute("display", "");
  }

  // Every shown node the dragged rectangle touches is selected; a click that
  // did not drag clears the selection.
  function finishMarquee() {
    var m = marquee;
    marquee = null;
    box.setAttribute("display", "none");
    if (Math.hypot(m.x1 - m.x0, m.y1 - m.y0) < 4) {
      if (!m.add) selected = {};
    } else {
      var left = (Math.min(m.x0, m.x1) - view.x) / view.k / G, right = (Math.max(m.x0, m.x1) - view.x) / view.k / G;
      var top = (Math.min(m.y0, m.y1) - view.y) / view.k / G, bottom = (Math.max(m.y0, m.y1) - view.y) / view.k / G;
      if (!m.add) selected = {};
      shown().forEach(function (n) {
        if (n.x < right && left < n.x + n.w && n.y < bottom && top < n.y + n.h) selected[n.name] = true;
      });
    }
    paintSelection();
  }

  svg.addEventListener("pointermove", function (event) {
    if (marquee && marquee.id === event.pointerId) {
      var at = local(event);
      marquee.x1 = at[0];
      marquee.y1 = at[1];
      drawMarquee();
      return;
    }
    if (!pointers[event.pointerId]) return;
    var before = pointers[event.pointerId];
    var now = local(event);
    pointers[event.pointerId] = now;
    var ids = Object.keys(pointers);
    if (ids.length === 1) {
      view.x += now[0] - before[0];
      view.y += now[1] - before[1];
      apply();
    } else if (ids.length === 2) {
      var p = pointers[ids[0]], q = pointers[ids[1]];
      var distance = Math.hypot(p[0] - q[0], p[1] - q[1]);
      if (pinch) zoomAt((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, distance / pinch);
      pinch = distance;
    }
  });
  function release(event) {
    if (marquee && marquee.id === event.pointerId) { finishMarquee(); return; }
    delete pointers[event.pointerId];
    pinch = null;
    if (!Object.keys(pointers).length) svg.classList.remove("grabbing");
  }
  svg.addEventListener("pointerup", release);
  svg.addEventListener("pointercancel", release);

  function center(factor) {
    var box = svg.getBoundingClientRect();
    zoomAt(box.width / 2, box.height / 2, factor);
  }
  document.getElementById("car-zoom-in").addEventListener("click", function () { center(1.25); });
  document.getElementById("car-zoom-out").addEventListener("click", function () { center(0.8); });
  document.getElementById("car-fit").addEventListener("click", fit);

  build();
  buildFilter();
  refresh();
  apply(true);
  // The tab is hidden until opened, so there is no size to fit to before that.
  var fitted = restored;
  new ResizeObserver(function () {
    if (!fitted) fitted = fit(true);
  }).observe(svg);
})();
"""
