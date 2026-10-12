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

// sizes: {name: {w, h}}. Resolves to {name: [x, y]}.
export async function layout(data, sizes) {
  const graph = {
    id: "car",
    layoutOptions: options,
    children: data.nodes.map((n) => ({ id: n.name, width: sizes[n.name].w, height: sizes[n.name].h })),
    edges: data.links.map((l, i) => ({ id: `e${i}`, sources: [l.a], targets: [l.b] })),
  };
  const done = await elk.layout(graph);
  return Object.fromEntries(done.children.map((c) => [c.id, [snap(c.x), snap(c.y)]]));
}
