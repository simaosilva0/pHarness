// The first placement: ELK's layered layout of the boxes and devices, with the
// cables as links. Only a starting point: every node can be dragged afterwards.
import ELK from "elkjs/lib/elk.bundled.js";

const elk = new ELK();
const SNAP = 10;
const snap = (v) => Math.round(v / SNAP) * SNAP;

const options = {
  "elk.algorithm": "layered",
  "elk.direction": "DOWN",
  "elk.spacing.nodeNode": "40",
  "elk.spacing.componentComponent": "60",
  "elk.layered.spacing.nodeNodeBetweenLayers": "90",
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
};

const GAP = 20;

// Moves free nodes out of whatever they overlap; pinned nodes never move.
function clear(at, sizes, pinned) {
  const hit = (a, b) => {
    const dx = Math.min(at[a][0] + sizes[a].w, at[b][0] + sizes[b].w) - Math.max(at[a][0], at[b][0]) + GAP;
    const dy = Math.min(at[a][1] + sizes[a].h, at[b][1] + sizes[b].h) - Math.max(at[a][1], at[b][1]) + GAP;
    return dx > 0 && dy > 0 ? [dx, dy] : null;
  };
  const names = Object.keys(at);
  for (let pass = 0; pass < 60; pass++) {
    let moved = false;
    for (const a of names) {
      if (pinned[a]) continue;
      for (const b of names) {
        const over = a !== b && hit(a, b);
        if (!over) continue;
        const [dx, dy] = over;
        const ca = [at[a][0] + sizes[a].w / 2, at[a][1] + sizes[a].h / 2];
        const cb = [at[b][0] + sizes[b].w / 2, at[b][1] + sizes[b].h / 2];
        if (dx < dy) at[a][0] += ca[0] < cb[0] ? -dx : dx;
        else at[a][1] += ca[1] < cb[1] ? -dy : dy;
        moved = true;
      }
    }
    if (!moved) break;
  }
}

// sizes: {name: {w, h}}; pinned: {name: [x, y]}, which stay exactly where they are.
// ELK places everything, the result is shifted so that it lines up with the
// pinned nodes, and free nodes that end up on top of something are pushed aside.
// Resolves to {name: [x, y]}.
export async function layout(data, sizes, pinned = {}) {
  const graph = {
    id: "car",
    layoutOptions: options,
    children: data.nodes.map((n) => ({ id: n.name, width: sizes[n.name].w, height: sizes[n.name].h })),
    edges: data.links.map((l, i) => ({ id: `e${i}`, sources: [l.a], targets: [l.b] })),
  };
  const done = await elk.layout(graph);
  const fixed = Object.keys(pinned).filter((n) => done.children.some((c) => c.id === n));
  const shift = fixed.length
    ? [0, 1].map((k) => snap(fixed.reduce((sum, n) => sum + pinned[n][k] - done.children.find((c) => c.id === n)[k ? "y" : "x"], 0) / fixed.length))
    : [0, 0];
  const at = Object.fromEntries(done.children.map((c) =>
    [c.id, pinned[c.id] ? [...pinned[c.id]] : [snap(c.x) + shift[0], snap(c.y) + shift[1]]]));
  if (fixed.length) clear(at, sizes, pinned);
  for (const n of Object.keys(at)) if (!pinned[n]) at[n] = [snap(at[n][0]), snap(at[n][1])];
  return at;
}
