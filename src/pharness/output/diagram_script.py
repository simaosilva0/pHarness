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
  var vias = {};   // a point a cable was dragged through, by cable key: [x, y]
  var ends = {};   // the side the user gave each end of a cable, by cable key: [first, second]

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

  var DIRS = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] };

  function clamp(value, lo, hi) {
    return Math.max(lo, Math.min(hi, value));
  }

  // The side each end of a link leaves by: the one the user chose, else the
  // sides facing each other, across when there is a gap between the nodes
  // sideways, along otherwise.
  function chosen(link) {
    var own = ends[link.key] || [];
    var a = nodes[link.a], b = nodes[link.b];
    var gapX = Math.max(a.x - (b.x + b.w), b.x - (a.x + a.w));
    var gapY = Math.max(a.y - (b.y + b.h), b.y - (a.y + a.h));
    var auto;
    if (gapX > 0 || gapY <= 0) auto = a.x + a.w / 2 < b.x + b.w / 2 ? ["right", "left"] : ["left", "right"];
    else auto = a.y + a.h / 2 < b.y + b.h / 2 ? ["bottom", "top"] : ["top", "bottom"];
    return [own[0] || auto[0], own[1] || auto[1]];
  }

  function capacity(node, side) {
    return (side === "left" || side === "right" ? node.h : node.w) - 1;
  }

  // Spread the links on each side of a node over distinct cells, ordered by
  // where they go, so two cables do not share a port. A side with more links
  // than cells gives the ones that look least that way to a side with room;
  // ends the user placed stay where they are.
  function ports(links) {
    var onSide = {};
    var add = function (port) {
      var key = port.node.name + "|" + port.side;
      (onSide[key] = onSide[key] || []).push(port);
    };
    links.forEach(function (link) {
      var a = nodes[link.a], b = nodes[link.b];
      var s = chosen(link);
      var own = ends[link.key] || [];
      link.sides = s;
      add({ link: link, node: a, other: b, side: s[0], end: 0, fixed: !!own[0] });
      add({ link: link, node: b, other: a, side: s[1], end: 1, fixed: !!own[1] });
    });
    var look = function (port) {
      var d = DIRS[port.side], n = port.node, o = port.other;
      return d[0] * (o.x + o.w / 2 - n.x - n.w / 2) + d[1] * (o.y + o.h / 2 - n.y - n.h / 2);
    };
    var order = { right: ["top", "bottom", "left"], left: ["top", "bottom", "right"],
                  top: ["left", "right", "bottom"], bottom: ["left", "right", "top"] };
    for (var pass = 0; pass < 3; pass++) {
      Object.keys(onSide).forEach(function (key) {
        var list = onSide[key];
        while (list.length > capacity(list[0].node, list[0].side)) {
          var loose = list.filter(function (port) { return !port.fixed; });
          if (!loose.length) break;
          var port = loose.reduce(function (worst, next) { return look(next) < look(worst) ? next : worst; });
          var home = order[port.side].filter(function (side) {
            return (onSide[port.node.name + "|" + side] || []).length < capacity(port.node, side);
          })[0];
          if (!home) break;
          list.splice(list.indexOf(port), 1);
          port.side = home;
          port.link.sides[port.end] = home;
          add(port);
        }
      });
    }
    Object.keys(onSide).forEach(function (key) {
      var list = onSide[key];
      if (!list.length) return;
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

  function portAt(node, side, at) {
    if (side === "left") return [node.x, at];
    if (side === "right") return [node.x + node.w, at];
    if (side === "top") return [at, node.y];
    return [at, node.y + node.h];
  }

  // --- finding a way for each cable ---------------------------------------------
  //
  // A cable runs on the grid lines from the side of one node to the side of
  // another, around every node, bending as little as it can. Cables may cross
  // but never share a line: each takes lines the cables before it did not.
  // The cables a user has placed are routed first, then the short ones.

  var OFF = 1000, SPAN = 4000;   // grid points are numbered (x + OFF) * SPAN + (y + OFF)
  var STEP = [[1, 0], [0, 1], [-1, 0], [0, -1]];
  var TURN = 4, CROSS = 3;
  var solid = {};        // grid points inside a node
  var used = {};         // unit pieces of line taken: "h|x|y" from (x, y) to (x + 1, y), "v|x|y" down
  var through = {};      // grid points a cable passes along: 1 across, 2 down
  var reserved = {};     // the grid point just outside each cable's ends, kept for that cable
  var routing = null;    // the key of the cable being routed

  function number(x, y) { return (x + OFF) * SPAN + (y + OFF); }

  // Where a link's two ends are, a cell out of their sides.
  function endsOf(link) {
    var s = link.sides;
    var p = portAt(nodes[link.a], s[0], link.at0), q = portAt(nodes[link.b], s[1], link.at1);
    var d0 = DIRS[s[0]], d1 = DIRS[s[1]];
    return { p: p, q: q, d0: d0, d1: d1, p1: [p[0] + d0[0], p[1] + d0[1]], q1: [q[0] + d1[0], q[1] + d1[1]] };
  }

  function resetBoard(list) {
    solid = {};
    used = {};
    through = {};
    reserved = {};
    list.forEach(function (link) {
      var e = endsOf(link);
      reserved[number(e.p1[0], e.p1[1])] = link.key;
      reserved[number(e.q1[0], e.q1[1])] = link.key;
    });
    data.nodes.forEach(function (n) {
      for (var x = n.x; x <= n.x + n.w; x++) {
        for (var y = n.y; y <= n.y + n.h; y++) solid[number(x, y)] = true;
      }
    });
  }

  // The unit pieces of line a path lies on.
  function pieces(points, take) {
    for (var i = 1; i < points.length; i++) {
      var a = points[i - 1], b = points[i];
      if (a[0] === b[0]) {
        for (var y = Math.min(a[1], b[1]); y < Math.max(a[1], b[1]); y++) take("v|" + a[0] + "|" + y);
      } else {
        for (var x = Math.min(a[0], b[0]); x < Math.max(a[0], b[0]); x++) take("h|" + x + "|" + a[1]);
      }
    }
  }

  // A routed cable's lines are taken, and the grid points it passes along are
  // noted, so later cables keep off them and cross it at a cost.
  function claimLine(points) {
    pieces(points, function (key) { used[key] = true; });
    for (var i = 1; i < points.length; i++) {
      var a = points[i - 1], b = points[i];
      var across = a[1] === b[1];
      for (var x = Math.min(a[0], b[0]); x <= Math.max(a[0], b[0]); x++) {
        for (var y = Math.min(a[1], b[1]); y <= Math.max(a[1], b[1]); y++) {
          through[number(x, y)] = (through[number(x, y)] || 0) | (across ? 1 : 2);
        }
      }
    }
  }

  function pieceKey(x, y, d) {
    // the unit piece of line from (x, y) one step in direction d
    if (d === 0) return "h|" + x + "|" + y;
    if (d === 2) return "h|" + (x - 1) + "|" + y;
    if (d === 1) return "v|" + x + "|" + y;
    return "v|" + x + "|" + (y - 1);
  }

  // A binary heap of [cost, state].
  function push(heap, item) {
    heap.push(item);
    var i = heap.length - 1;
    while (i > 0) {
      var parent = (i - 1) >> 1;
      if (heap[parent][0] <= heap[i][0]) break;
      var swap = heap[parent]; heap[parent] = heap[i]; heap[i] = swap;
      i = parent;
    }
  }
  function pop(heap) {
    var top = heap[0], last = heap.pop();
    if (heap.length) {
      heap[0] = last;
      var i = 0;
      for (;;) {
        var l = 2 * i + 1, r = l + 1, m = i;
        if (l < heap.length && heap[l][0] < heap[m][0]) m = l;
        if (r < heap.length && heap[r][0] < heap[m][0]) m = r;
        if (m === i) break;
        var swap = heap[m]; heap[m] = heap[i]; heap[i] = swap;
        i = m;
      }
    }
    return top;
  }

  // The cheapest way from `from` (leaving in direction `dir`) to `to` inside
  // `box` ([x0, y0, x1, y1]), or null. `extra` are pieces of line taken by the
  // cable's own earlier part.
  function search(from, dir, to, box, extra) {
    var w = box[2] - box[0] + 1, h = box[3] - box[1] + 1;
    var cost = new Float32Array(w * h * 4).fill(Infinity);
    var before = new Int32Array(w * h * 4).fill(-1);
    var id = function (x, y, d) { return (((x - box[0]) * h) + (y - box[1])) * 4 + d; };
    var heap = [];
    var start = id(from[0], from[1], dir);
    cost[start] = 0;
    push(heap, [Math.abs(from[0] - to[0]) + Math.abs(from[1] - to[1]), start]);
    while (heap.length) {
      var state = pop(heap)[1];
      var d = state % 4, cell = (state - d) / 4, y = cell % h + box[1], x = (cell - (cell % h)) / h + box[0];
      if (x === to[0] && y === to[1]) {
        var found = [[x, y]], at = state;
        while (before[at] >= 0) {
          at = before[at];
          var pd = at % 4, pc = (at - pd) / 4;
          found.push([(pc - (pc % h)) / h + box[0], pc % h + box[1]]);
        }
        return found.reverse();
      }
      for (var nd = 0; nd < 4; nd++) {
        if (nd === (d + 2) % 4) continue;
        var nx = x + STEP[nd][0], ny = y + STEP[nd][1];
        if (nx < box[0] || nx > box[2] || ny < box[1] || ny > box[3]) continue;
        var goal = nx === to[0] && ny === to[1];
        if (solid[number(nx, ny)] && !goal) continue;
        var owner = reserved[number(nx, ny)];
        if (owner !== undefined && owner !== routing && !goal) continue;   // another cable's end
        var key = pieceKey(x, y, nd);
        if (used[key] || extra[key]) continue;
        var more = 1 + (nd !== d ? TURN : 0);
        var crossing = through[number(nx, ny)];
        if (crossing && !goal && (crossing & (nd % 2 === 0 ? 2 : 1)) && !(crossing & (nd % 2 === 0 ? 1 : 2))) more += CROSS;
        var next = id(nx, ny, nd);
        var total = cost[id(x, y, d)] + more;
        if (total < cost[next]) {
          cost[next] = total;
          before[next] = state;
          push(heap, [total + Math.abs(nx - to[0]) + Math.abs(ny - to[1]), next]);
        }
      }
    }
    return null;
  }

  // The grid points a path turns at, between its ends, without the ones in a
  // straight line.
  function corners(points) {
    var out = [points[0]];
    for (var i = 1; i < points.length - 1; i++) {
      var a = points[i - 1], b = points[i], c = points[i + 1];
      if ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) !== 0) out.push(b);
    }
    out.push(points[points.length - 1]);
    return out;
  }

  // Around the two ends, a box to search in, wider each time the way is not found.
  function reach(list, margin) {
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    list.forEach(function (pt) {
      x0 = Math.min(x0, pt[0]); y0 = Math.min(y0, pt[1]); x1 = Math.max(x1, pt[0]); y1 = Math.max(y1, pt[1]);
    });
    return [x0 - margin, y0 - margin, x1 + margin, y1 + margin];
  }

  function wayBetween(from, dir, to, via) {
    var legs = via ? [[from, dir, via], [via, null, to]] : [[from, dir, to]];
    var whole = null, extra = {};
    for (var m = 0, margins = [8, 24, 80]; m < margins.length; m++) {
      whole = [];
      extra = {};
      var ok = true;
      for (var i = 0; i < legs.length; i++) {
        var leg = legs[i];
        var started = leg[1];
        if (started === null) {   // after a waypoint: any way out of it
          var last = whole[whole.length - 1], before = whole[whole.length - 2];
          started = before ? (last[0] > before[0] ? 0 : last[0] < before[0] ? 2 : last[1] > before[1] ? 1 : 3) : 0;
        }
        var found = search(leg[0], started, leg[2], reach([from, to, via || from], margins[m]), extra);
        if (!found) { ok = false; break; }
        pieces(found, function (key) { extra[key] = true; });
        whole = whole.concat(whole.length ? found.slice(1) : found);
      }
      if (ok) return whole;
    }
    return null;
  }

  // A link's route and its handles. The ends stand a cell out of their sides;
  // between them the way is found on the grid.
  function route(link) {
    var e = endsOf(link);
    var p = e.p, q = e.q, d0 = e.d0, p1 = e.p1, q1 = e.q1;
    routing = link.key;
    var dir = STEP.findIndex(function (st) { return st[0] === d0[0] && st[1] === d0[1]; });
    var via = vias[link.key];
    if (via && solid[number(via[0], via[1])]) via = null;   // a node has taken its place
    var way = wayBetween(p1, dir, q1, via);
    var inner;
    if (way) {
      inner = way;
    } else {   // no way round: straight through, as a last resort
      inner = [p1, d0[0] === 0 ? [q1[0], p1[1]] : [p1[0], q1[1]], q1];
    }
    var points = corners([p].concat(inner, [q]));
    claimLine(points);
    link.points = points;
    link.base = { handles: { ends: [p, q], mid: middle(points, via) } };
    return points;
  }

  // The point to grab in the middle: where the user put it, else the grid point
  // halfway along a cable that bends; none on a straight cable.
  function middle(points, via) {
    if (points.length <= 2) return null;
    if (via) return via;
    var total = 0, i;
    for (i = 1; i < points.length; i++) total += Math.abs(points[i][0] - points[i - 1][0]) + Math.abs(points[i][1] - points[i - 1][1]);
    var left = Math.floor(total / 2);
    for (i = 1; i < points.length; i++) {
      var a = points[i - 1], b = points[i];
      var length = Math.abs(b[0] - a[0]) + Math.abs(b[1] - a[1]);
      if (left <= length) return [a[0] + Math.sign(b[0] - a[0]) * left, a[1] + Math.sign(b[1] - a[1]) * left];
      left -= length;
    }
    return points[points.length - 1];
  }

  function path(points) {
    return points.map(function (pt) { return (pt[0] * G) + "," + (pt[1] * G); }).join(" ");
  }

  // A cable's width follows its wires: not realistic, but a fat cable looks fat.
  function thickness(wires) {
    return Math.min(12, 2 + 1.1 * Math.sqrt(Math.max(wires, 1)));
  }

  // --- drawing --------------------------------------------------------------

  // The cables as drawn: one per pair of nodes with its cables bundled, or one
  // for each cable.
  var drawn = [];

  // Every cable, whatever the filter shows, so none of them moves with it.
  function items() {
    if (options.bundled) return data.links.map(function (link) {
      return { key: link.a + "|" + link.b, a: link.a, b: link.b, wires: link.wires, cables: link.cables,
               href: link.cables[0] && link.cables[0].href };
    });
    var list = [];
    data.links.forEach(function (link) {
      link.cables.forEach(function (cable) {
        list.push({ key: link.a + "|" + link.b + "|" + cable.name, a: link.a, b: link.b, wires: cable.wires,
                    cables: [cable], href: cable.href });
      });
    });
    return list;
  }

  var cablesLayer, nodesLayer, handlesLayer;
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
    handlesLayer = make("g", { "class": "car-handles", display: "none" }, world);
    makeHandles();

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

  // The cables, again: when a node moves or a switch changes. All are routed;
  // only those between shown nodes are drawn.
  function drawCables() {
    while (cablesLayer.firstChild) cablesLayer.removeChild(cablesLayer.firstChild);
    var list = items();
    ports(list);
    resetBoard(list);
    drawn = [];
    // cables the user placed are routed first, so they get the lines they
    // chose; then the short ones, which have the least room to spare
    var length = function (item) {
      var a = nodes[item.a], b = nodes[item.b];
      return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
    };
    var mine = function (item) { return vias[item.key] !== undefined || ends[item.key] ? 1 : 0; };
    list.slice().sort(function (x, y) { return mine(y) - mine(x) || length(x) - length(y); }).forEach(function (item) {
      var points = route(item);
      if (!visible(nodes[item.a]) || !visible(nodes[item.b])) return;
      var line = make("polyline", { points: path(points), "stroke-width": thickness(item.wires) }, cablesLayer);
      line.setAttribute("class", "car-cable");
      // a wider line, drawn on top and invisible, so a thin cable is easy to point at
      var hit = make("polyline", { points: path(points), "stroke-width": 14 }, cablesLayer);
      hit.setAttribute("class", "car-hit");
      if (item.href) hit.style.cursor = "pointer";
      cableEvents(item, hit);
      drawn.push({ item: item, line: line });
    });
    svg.classList.toggle("hide-cables", !options.show);
    if (current && !current.kind) {   // the old drawing's cable: find its twin
      current = (drawn.filter(function (entry) { return entry.item.key === current.key; })[0] || {}).item || null;
    }
    focus(current);
    placeHandles();
  }

  // Pointing at a cable names it and shows its handles; a click goes to its
  // cable page; a double click puts it back where the tool had it.
  function cableEvents(item, hit) {
    var waiting = null;
    hit.addEventListener("pointerenter", function (event) {
      focus(item);
      tip(item, event);
      showHandles(item);
    });
    hit.addEventListener("pointermove", function (event) { tip(item, event); });
    hit.addEventListener("pointerleave", function () { focus(null); tip(null); hideSoon(); });
    hit.addEventListener("pointerdown", function (event) {
      if (event.button !== 0 || panKey(event)) return;
      event.stopPropagation();   // not the start of a selection
    });
    hit.addEventListener("click", function () {
      clearTimeout(waiting);
      if (item.href) waiting = setTimeout(function () { jump(item.href); }, 250);   // unless it is a double click
    });
    hit.addEventListener("dblclick", function () {
      clearTimeout(waiting);
      delete vias[item.key];
      delete ends[item.key];
      drawCables();
      save();
    });
  }

  // --- the handles of a cable -------------------------------------------------

  // The cable pointed at has a handle on each end, which snaps to a side of its
  // box or device, and one on the middle run (when it has one), which slides
  // along the grid.
  var activeKey = null, hideTimer = null, grabbed = null;
  var handles = [];

  function activeItem() {
    var found = drawn.filter(function (entry) { return entry.item.key === activeKey; })[0];
    return found ? found.item : null;
  }

  function showHandles(item) {
    clearTimeout(hideTimer);
    activeKey = item.key;
    placeHandles();
  }

  function hideSoon() {
    if (grabbed) return;
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideNow, 350);
  }

  function hideNow() {
    clearTimeout(hideTimer);
    activeKey = null;
    placeHandles();
  }

  function placeHandles() {
    var item = options.show ? activeItem() : null;
    handlesLayer.setAttribute("display", item ? "" : "none");
    if (!item) return;
    var spots = [item.base.handles.ends[0], item.base.handles.ends[1], item.base.handles.mid];
    handles.forEach(function (el, i) {
      el.setAttribute("display", spots[i] ? "" : "none");
      if (!spots[i]) return;
      el.setAttribute("cx", spots[i][0] * G);
      el.setAttribute("cy", spots[i][1] * G);
      el.setAttribute("r", 7 / view.k);
    });
    handles[2].style.cursor = "move";
  }

  // The side of a node the point is nearest, by direction from its centre.
  function nearestSide(node, x, y) {
    var nx = (x - node.x - node.w / 2) / (node.w / 2), ny = (y - node.y - node.h / 2) / (node.h / 2);
    if (Math.abs(nx) > Math.abs(ny)) return nx < 0 ? "left" : "right";
    return ny < 0 ? "top" : "bottom";
  }

  function moveHandle(index, event) {
    var item = activeItem();
    if (!item) return;
    var at = local(event);
    var x = (at[0] - view.x) / view.k / G, y = (at[1] - view.y) / view.k / G;
    if (index === 2) {
      var cell = [Math.round(x), Math.round(y)];
      if (solid[number(cell[0], cell[1])]) return;   // not inside a node
      var held = vias[item.key];
      if (held && held[0] === cell[0] && held[1] === cell[1]) return;
      vias[item.key] = cell;
    } else {
      var side = nearestSide(nodes[index === 0 ? item.a : item.b], x, y);
      if (side === item.sides[index]) return;
      ends[item.key] = ends[item.key] || [null, null];
      ends[item.key][index] = side;
      delete vias[item.key];   // the old waypoint belonged to the old way round
    }
    drawCables();
  }

  function makeHandles() {
    for (var index = 0; index < 3; index++) {
      (function (index) {
        var el = make("circle", { "class": "car-handle" + (index === 2 ? " mid" : ""), display: "none" }, handlesLayer);
        el.addEventListener("pointerenter", function () { clearTimeout(hideTimer); });
        el.addEventListener("pointerleave", hideSoon);
        el.addEventListener("pointerdown", function (event) {
          if (event.button !== 0 || panKey(event)) return;
          event.stopPropagation();
          el.setPointerCapture(event.pointerId);
          grabbed = { id: event.pointerId };
          tip(null);
        });
        el.addEventListener("pointermove", function (event) {
          if (grabbed && grabbed.id === event.pointerId) moveHandle(index, event);
        });
        function drop(event) {
          if (!grabbed || grabbed.id !== event.pointerId) return;
          grabbed = null;
          save();
          hideSoon();
        }
        el.addEventListener("pointerup", drop);
        el.addEventListener("pointercancel", drop);
        // a double click puts back what the handle changed
        el.addEventListener("dblclick", function () {
          var item = activeItem();
          if (!item) return;
          if (index === 2) {
            delete vias[item.key];
          } else if (ends[item.key]) {
            ends[item.key][index] = null;
            delete vias[item.key];
          }
          drawCables();
          save();
        });
        handles.push(el);
      })(index);
    }
  }

  function jump(href) {
    location.hash = "#" + href;
  }

  // A box goes to its pinout; a device to the first cable that reaches it.
  function pageOf(node) {
    if (node.href) return node.href;
    for (var i = 0; i < data.links.length; i++) {
      var link = data.links[i];
      if ((link.a === node.name || link.b === node.name) && link.cables[0] && link.cables[0].href) return link.cables[0].href;
    }
    return null;
  }

  // --- selecting and moving nodes -------------------------------------------

  function paintSelection() {
    data.nodes.forEach(function (node) {
      groups[node.name].classList.toggle("selected", !!selected[node.name]);
    });
  }

  function overlaps(moving, dx, dy) {
    return data.nodes.some(function (other) {
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
               shift: event.shiftKey,
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
      } else if (!drag.shift) {
        selected = {};
        selected[node.name] = true;
        paintSelection();
        var page = event.type === "pointerup" ? pageOf(node) : null;
        if (page) jump(page);
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
      Object.keys(saved.ends || {}).forEach(function (key) {
        var pair = saved.ends[key];
        if (Array.isArray(pair) && pair.length === 2 && pair.every(function (side) { return side === null || DIRS[side]; })) ends[key] = pair;
      });
      Object.keys(saved.vias || {}).forEach(function (key) {
        var at = saved.vias[key];
        if (Array.isArray(at) && at.length === 2 && whole(at[0]) && whole(at[1])) vias[key] = at;
      });
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
      localStorage.setItem(storeKey, JSON.stringify({ nodes: moved, view: view, options: options, hidden: Object.keys(hidden), vias: vias, ends: ends }));
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
      hideNow();
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
    devicesBox = devices;
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

    var names = element("datalist", bar, "", { id: "car-names" });
    data.nodes.forEach(function (n) { element("option", names, "", { value: n.name }); });
    var search = element("input", bar, "", { type: "search", placeholder: "Find a box or device…", list: "car-names",
                                             "class": "search", "aria-label": "Find a box or device" });
    function go() {
      var node = find(search.value);
      search.classList.toggle("nomatch", !node && search.value.trim() !== "");
      if (node) reveal(node);
    }
    search.addEventListener("change", go);
    search.addEventListener("keydown", function (event) { if (event.key === "Enter") go(); });
    search.addEventListener("input", function () { search.classList.remove("nomatch"); });

    element("button", bar, "SVG", { "class": "export", title: "Save what is shown as an SVG image" }).addEventListener("click", saveSvg);
    element("button", bar, "PNG", { title: "Save what is shown as a PNG image" }).addEventListener("click", savePng);
  }

  // --- search and export ----------------------------------------------------

  var devicesBox = null;

  // The node whose name is, starts with or contains the text, in that order.
  function find(text) {
    var t = text.trim().toLowerCase();
    if (!t) return null;
    var tests = [function (n) { return n === t; }, function (n) { return n.indexOf(t) === 0; },
                 function (n) { return n.indexOf(t) >= 0; }];
    for (var i = 0; i < tests.length; i++) {
      var hit = data.nodes.filter(function (n) { return tests[i](n.name.toLowerCase()); })[0];
      if (hit) return hit;
    }
    return null;
  }

  // Bring a node into view: shown if the filter hid it, selected, centered.
  function reveal(node) {
    delete hidden[node.name];
    if (node.kind === "device" && !options.devices) {
      options.devices = true;
      if (devicesBox) devicesBox.checked = true;
    }
    selected = {};
    selected[node.name] = true;
    refresh();
    var box = svg.getBoundingClientRect();
    view.k = Math.max(view.k, 0.6);
    view.x = box.width / 2 - (node.x + node.w / 2) * G * view.k;
    view.y = box.height / 2 - (node.y + node.h / 2) * G * view.k;
    apply();
    save();
    var group = groups[node.name];
    group.classList.remove("found");
    void group.getBoundingClientRect();
    group.classList.add("found");
  }

  function download(name, blob) {
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
  }

  function xml(text) {
    return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // What is on screen as a standalone SVG on white: the shown nodes and, when
  // the cables are on, the cables between them; the view does not matter.
  function exportSvg() {
    var list = shown();
    if (!list.length) return null;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    function grow(x, y) {
      minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
    list.forEach(function (n) { grow(n.x, n.y); grow(n.x + n.w, n.y + n.h); });
    var lines = options.show ? drawn : [];
    lines.forEach(function (entry) { entry.item.points.forEach(function (pt) { grow(pt[0], pt[1]); }); });
    var x = (minX - 2) * G, y = (minY - 2) * G, w = (maxX - minX + 4) * G, h = (maxY - minY + 4) * G;
    var out = ['<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="' + x + " " + y + " " + w + " " + h +
               '" font-family="system-ui, sans-serif">',
               '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="#ffffff"/>'];
    lines.forEach(function (entry) {
      out.push('<polyline points="' + path(entry.item.points) + '" fill="none" stroke="#6a6f78" stroke-width="' +
               thickness(entry.item.wires) + '" stroke-linejoin="round"/>');
    });
    list.forEach(function (n) {
      var box = n.kind === "box";
      out.push('<rect x="' + n.x * G + '" y="' + n.y * G + '" width="' + n.w * G + '" height="' + n.h * G + '" rx="6" fill="' +
               (box ? "#f3f4f6" : "#ffffff") + '" stroke="' + (box ? "#1d1f23" : "#6a6f78") + '" stroke-width="' + (box ? 2 : 1.5) + '"/>');
      out.push('<text x="' + (n.x + n.w / 2) * G + '" y="' + ((n.y + n.h / 2) * G + (box ? -4 : 4)) +
               '" text-anchor="middle" fill="#1d1f23" font-size="' + (box ? 13 : 11) + '" font-weight="' + (box ? 600 : 500) + '">' + xml(n.name) + "</text>");
      if (n.info) {
        out.push('<text x="' + (n.x + n.w / 2) * G + '" y="' + ((n.y + n.h / 2) * G + 16) +
                 '" text-anchor="middle" fill="#6a6f78" font-size="11">' + xml(n.info) + "</text>");
      }
    });
    out.push("</svg>");
    return { text: out.join("\n"), width: w, height: h };
  }

  function exportName(ext) {
    var car = document.title.replace(/ pinout$/, "").replace(/[^A-Za-z0-9._-]+/g, "-") || "car";
    return car + "-car." + ext;
  }

  function saveSvg() {
    var image = exportSvg();
    if (image) download(exportName("svg"), new Blob([image.text], { type: "image/svg+xml" }));
  }

  function savePng() {
    var image = exportSvg();
    if (!image) return;
    var scale = Math.min(2, 8000 / Math.max(image.width, image.height));
    var picture = new Image();
    picture.onload = function () {
      var canvas = document.createElement("canvas");
      canvas.width = Math.round(image.width * scale);
      canvas.height = Math.round(image.height * scale);
      canvas.getContext("2d").drawImage(picture, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(function (blob) { if (blob) download(exportName("png"), blob); }, "image/png");
    };
    picture.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(image.text);
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
    vias = {};
    ends = {};
    drawCables();
    fit();
    save();
  });

  // --- zoom and pan ---------------------------------------------------------

  function apply(quiet) {
    world.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.k + ")");
    handles.forEach(function (el) { el.setAttribute("r", 7 / view.k); });
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
