// What the page remembers in this browser: where nodes were moved, the cables
// the user changed, what is hidden, the switches and the view. A different set of
// boxes and devices is a different car and starts from the default layout.

function hash(text) {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(16);
}

export function storeKeyFor(data) {
  return `pharness-car-rf:${document.title}:${hash(data.nodes.map((n) => n.name).sort().join("\n"))}`;
}

const number = (v) => typeof v === "number" && Number.isFinite(v);

// The saved state, or an empty one: anything unusable is left out.
export function load(key, data) {
  const out = { moved: {}, setup: {}, hidden: {}, options: {}, viewport: null };
  try {
    const saved = JSON.parse(localStorage.getItem(key));
    if (!saved) return out;
    const known = new Set(data.nodes.map((n) => n.name));
    for (const [name, at] of Object.entries(saved.moved || {})) {
      if (known.has(name) && Array.isArray(at) && at.length === 2 && at.every(number)) out.moved[name] = at;
    }
    for (const [k, one] of Object.entries(saved.setup || {})) {
      if (one && typeof one === "object") out.setup[k] = one;
    }
    for (const name of saved.hidden || []) if (known.has(name)) out.hidden[name] = true;
    out.options = saved.options || {};
    const v = saved.viewport;
    if (v && number(v.x) && number(v.y) && number(v.zoom) && v.zoom > 0) out.viewport = v;
  } catch (e) { /* no memory here: the default layout */ }
  return out;
}

export function save(key, state) {
  try {
    localStorage.setItem(key, JSON.stringify(state));
  } catch (e) { /* blocked or full: nothing is kept */ }
}
