import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, Controls, ConnectionMode, MiniMap, Panel, ReactFlow, ReactFlowProvider, useNodesState, useReactFlow,
} from "@xyflow/react";
import CarNode from "./CarNode.jsx";
import CableEdge from "./CableEdge.jsx";
import Toolbar from "./Toolbar.jsx";
import { plan } from "./routing.js";
import { sizeOf } from "./sizes.js";
import { load, save, storeKeyFor } from "./store.js";
import { savePng, saveSvg, svgOf } from "./exporting.js";

const nodeTypes = { car: CarNode };
const edgeTypes = { cable: CableEdge };

// The page's light or dark, which the page's own switch changes.
function usePageTheme() {
  const read = () => document.documentElement.getAttribute("data-theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const [theme, setTheme] = useState(read);
  useEffect(() => {
    const watch = new MutationObserver(() => setTheme(read()));
    watch.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", () => setTheme(read()));
    return () => watch.disconnect();
  }, []);
  return theme;
}

// A cable's width follows its wires: not realistic, but a fat cable looks fat.
const thickness = (wires) => Math.min(10, 1.5 + 0.9 * Math.sqrt(Math.max(wires, 1)));

function Car({ data }) {
  const key = useMemo(() => storeKeyFor(data), [data]);
  const saved = useMemo(() => load(key, data), [key, data]);
  const grid = data.grid;
  const theme = usePageTheme();
  const flow = useReactFlow();
  const rootRef = useRef(null);

  const home = useMemo(() => data.nodes.map((n) => ({
    id: n.name, type: "car", position: { x: n.x * grid, y: n.y * grid },
    data: n,
  })), [data, grid]);
  const [nodes, setNodes, onNodesChange] = useNodesState(home.map((n) => {
    const at = saved.moved[n.id];
    return at ? { ...n, position: { x: at[0], y: at[1] } } : n;
  }));

  const [hidden, setHidden] = useState(saved.hidden);
  const [options, setOptions] = useState({ show: true, bundled: true, devices: true, text: 1, ...saved.options });
  const sizes = useMemo(() => Object.fromEntries(data.nodes.map((n) => [n.name, sizeOf(n, grid, options.text)])),
    [data, grid, options.text]);
  const [setup, setSetup] = useState(saved.setup);   // what the user did to a cable: {s, t}
  const [hover, setHover] = useState(null);
  const [tip, setTip] = useState(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [found, setFound] = useState(null);

  const isHidden = (n) => hidden[n.id] || (n.data.kind === "device" && !options.devices);
  const shownNodes = useMemo(() => nodes.map((n) => ({
    ...n, hidden: !!isHidden(n), data: { ...n.data, ...sizes[n.id], found: found === n.id },
  })), [nodes, hidden, options.devices, found, sizes]);

  // What is remembered, a moment after the last change.
  const view = useRef(saved.viewport);
  useEffect(() => {
    const wait = setTimeout(() => {
      const moved = {};
      nodes.forEach((n, i) => {
        if (n.position.x !== home[i].position.x || n.position.y !== home[i].position.y) moved[n.id] = [n.position.x, n.position.y];
      });
      save(key, { moved, setup, hidden: Object.keys(hidden), options, viewport: view.current });
    }, 300);
    return () => clearTimeout(wait);
  }, [nodes, setup, hidden, options, key, home]);

  // --- the cables ---

  const items = useMemo(() => {
    if (options.bundled) return data.links.map((l) => ({
      key: `${l.a}|${l.b}`, a: l.a, b: l.b, wires: l.wires, cables: l.cables, href: l.cables[0]?.href,
    }));
    return data.links.flatMap((l) => l.cables.map((c) => ({
      key: `${l.a}|${l.b}|${c.name}`, a: l.a, b: l.b, wires: c.wires, cables: [c], href: c.href,
    })));
  }, [data, options.bundled]);

  const edges = useMemo(() => {
    const at = Object.fromEntries(nodes.map((n) => [n.id, { x: n.position.x, y: n.position.y, ...sizes[n.id] }]));
    return plan(items, at, setup).map(({ item, s, t }) => ({
      id: item.key, source: item.a, target: item.b, sourceHandle: s, targetHandle: t, type: "cable",
      style: { strokeWidth: thickness(item.wires) },
      zIndex: hover === item.key ? 20 : 0,   // the cable pointed at is drawn over the nodes
      className: hover && (hover === item.key || hover === item.a || hover === item.b) ? "hot" : hover ? "dim" : "",
      data: { item },
    }));
  }, [items, nodes, setup, hover, sizes]);

  // A cable end dropped on a handle of the node it was on goes to that side and
  // slot, and stays there; the other end is left as it was.
  const onReconnect = useCallback((old, connection) => {
    if (connection.source !== old.source || connection.target !== old.target) return;
    setSetup((all) => {
      const one = { ...all[old.id] };
      if (connection.sourceHandle !== old.sourceHandle) one.s = connection.sourceHandle;
      if (connection.targetHandle !== old.targetHandle) one.t = connection.targetHandle;
      return { ...all, [old.id]: one };
    });
  }, []);

  // --- the filter ---

  const fitSoon = () => setTimeout(() => flow.fitView({ padding: 0.1, duration: 300 }), 50);

  const only = (names) => {
    const next = {};
    data.nodes.forEach((n) => { if (!names.includes(n.name)) next[n.name] = true; });
    setHidden(next);
    fitSoon();
  };
  const toggleBox = (name) => {
    const group = [name, ...data.nodes.filter((n) => n.owner === name).map((n) => n.name)];
    setHidden((all) => {
      const next = { ...all };
      group.forEach((g) => { if (all[name]) delete next[g]; else next[g] = true; });
      return next;
    });
  };

  // The node whose name is, starts with or contains the text, in that order.
  const find = (text) => {
    const t = text.trim().toLowerCase();
    const name = (n) => n.name.toLowerCase();
    const hit = data.nodes.find((n) => name(n) === t) || data.nodes.find((n) => name(n).startsWith(t)) ||
      data.nodes.find((n) => name(n).includes(t));
    if (!hit) return null;
    setHidden((all) => { const next = { ...all }; delete next[hit.name]; return next; });
    if (hit.kind === "device") setOptions((o) => ({ ...o, devices: true }));
    setNodes((all) => all.map((n) => ({ ...n, selected: n.id === hit.name })));
    const at = nodes.find((n) => n.id === hit.name);
    setTimeout(() => flow.setCenter(at.position.x + sizes[at.id].w / 2, at.position.y + sizes[at.id].h / 2,
      { zoom: Math.max(flow.getZoom(), 0.8), duration: 300 }), 50);
    setFound(hit.name);
    setTimeout(() => setFound(null), 1500);
    return hit;
  };

  const reset = () => {
    setNodes(home);
    setSetup({});
    fitSoon();
  };

  const picture = () => {
    const list = shownNodes.filter((n) => !n.hidden).map((n) => ({ ...n.data, x: n.position.x, y: n.position.y }));
    const edgeList = edges.filter((e) => !hidden[e.source] && !hidden[e.target] &&
      (options.devices || (nodes.find((n) => n.id === e.source).data.kind === "box" && nodes.find((n) => n.id === e.target).data.kind === "box")));
    return svgOf(list, edgeList, options.show, options.text);
  };

  // --- going to a pinout or cable ---

  const jump = (href) => { if (href) location.hash = `#${href}`; };
  const pageOf = (node) => node.data.href || data.links.find((l) => (l.a === node.id || l.b === node.id) && l.cables[0]?.href)?.cables[0].href;

  // The tab is hidden until opened, so there is no size to fit to before that.
  const fitted = useRef(!!saved.viewport);
  useEffect(() => {
    const watch = new ResizeObserver(() => {
      if (!fitted.current && rootRef.current.clientWidth > 0) {
        fitted.current = true;
        flow.fitView({ padding: 0.1 });
      }
    });
    watch.observe(rootRef.current);
    return () => watch.disconnect();
  }, [flow]);

  return (
    <div className="car" ref={rootRef} style={{ "--text": options.text }}>
      <Toolbar data={data} hidden={hidden} devices={options.devices} find={find} only={only} toggleBox={toggleBox}
               showDevices={(on) => setOptions((o) => ({ ...o, devices: on }))}
               onSvg={() => saveSvg(picture())} onPng={() => savePng(picture())} />
      <div className={`stage${options.show ? "" : " hide-cables"}${reconnecting ? " reconnecting" : ""}`}>
        <ReactFlow
          nodes={shownNodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} onNodesChange={onNodesChange}
          colorMode={theme} connectionMode={ConnectionMode.Loose} nodesConnectable={false} edgesFocusable={false}
          edgesReconnectable reconnectRadius={14} connectionRadius={30} onReconnect={onReconnect}
          onReconnectStart={() => setReconnecting(true)} onReconnectEnd={() => setReconnecting(false)}
          onEdgeMouseEnter={(_, e) => setHover(e.id)} onEdgeMouseLeave={() => { setHover(null); setTip(null); }}
          onEdgeMouseMove={(event, e) => setTip({ x: event.clientX, y: event.clientY, item: e.data.item })}
          onNodeMouseEnter={(_, n) => setHover(n.id)} onNodeMouseLeave={() => setHover(null)}
          onEdgeClick={(_, e) => jump(e.data.item.href)} onNodeClick={(_, n) => jump(pageOf(n))}
          onMoveEnd={(_, v) => { view.current = v; }}
          defaultViewport={saved.viewport || { x: 0, y: 0, zoom: 1 }}
          snapToGrid snapGrid={[10, 10]} selectionOnDrag panOnDrag={[1, 2]} panActivationKeyCode="Space"
          minZoom={0.1} maxZoom={4} deleteKeyCode={null} proOptions={{ hideAttribution: true }}
        >
          <Background gap={20} />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable />
          <Panel position="top-right" className="switches">
            <label><input type="checkbox" checked={options.show} onChange={(e) => setOptions((o) => ({ ...o, show: e.target.checked }))} /> Cables</label>
            <label><input type="checkbox" checked={options.bundled} onChange={(e) => setOptions((o) => ({ ...o, bundled: e.target.checked }))} /> Bundled</label>
            <label className="size" title="Size of the names on boxes and devices">Text
              <input type="range" min="0.7" max="2" step="0.1" value={options.text}
                     onChange={(e) => setOptions((o) => ({ ...o, text: Number(e.target.value) }))} />
            </label>
            <button onClick={reset} title="Put every box, device and cable back where the tool placed it">Reset layout</button>
          </Panel>
        </ReactFlow>
        {tip && options.show && (
          <div className="tip" style={{ left: tip.x - rootRef.current.getBoundingClientRect().left + 14, top: tip.y - rootRef.current.getBoundingClientRect().top + 14 }}>
            {tip.item.cables.slice(0, 8).map((c) => `${c.name} · ${c.wires} ${c.wires === 1 ? "wire" : "wires"}`).join("\n")}
            {tip.item.cables.length > 8 ? `\n+${tip.item.cables.length - 8} more` : ""}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App({ data }) {
  return <ReactFlowProvider><Car data={data} /></ReactFlowProvider>;
}
