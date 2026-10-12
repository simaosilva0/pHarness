import { useState } from "react";

// The bar above the diagram: what is shown, search, and saving a picture.
export default function Toolbar({ data, hidden, devices, showDevices, only, toggleBox, find, onSvg, onPng }) {
  const boxes = data.nodes.filter((n) => n.kind === "box");
  const [text, setText] = useState("");
  const [miss, setMiss] = useState(false);

  function go() {
    if (!text.trim()) return;
    setMiss(!find(text));
  }
  const kinds = [["bus", "Buses"], ["link", "Links"], ["chain", "Chains"]];

  return (
    <div className="filter">
      <button onClick={() => only(data.nodes.map((n) => n.name))}>All</button>
      <button onClick={() => only([])}>None</button>
      {boxes.map((box) => (
        <button key={box.name} className={`chip${hidden[box.name] ? " off" : ""}`} title={`Show or hide ${box.name} and its devices`}
                onClick={() => toggleBox(box.name)}>{box.name}</button>
      ))}
      <label><input type="checkbox" checked={devices} onChange={(e) => showDevices(e.target.checked)} /> Devices</label>
      <select value="" title="Show one box and the boxes it is cabled to"
              onChange={(e) => e.target.value && only(neighbours(data, e.target.value))}>
        <option value="">Box and neighbours…</option>
        {boxes.map((box) => <option key={box.name} value={box.name}>{box.name}</option>)}
      </select>
      <select value="" title="Show only what a bus, link or chain touches"
              onChange={(e) => {
                const pick = data.groups.find((g) => e.target.value === `${g.kind}:${g.name}`);
                if (pick) only(pick.members);
              }}>
        <option value="">Bus, link or chain…</option>
        {kinds.map(([kind, title]) => {
          const found = data.groups.filter((g) => g.kind === kind);
          return found.length ? (
            <optgroup key={kind} label={title}>
              {found.map((g) => <option key={g.name} value={`${kind}:${g.name}`}>{g.name}</option>)}
            </optgroup>
          ) : null;
        })}
      </select>
      <input type="search" className={`search${miss ? " nomatch" : ""}`} placeholder="Find a box or device…" list="car-names"
             aria-label="Find a box or device" value={text}
             onChange={(e) => { setText(e.target.value); setMiss(false); }}
             onKeyDown={(e) => e.key === "Enter" && go()} onBlur={go} />
      <datalist id="car-names">{data.nodes.map((n) => <option key={n.name} value={n.name} />)}</datalist>
      <button className="export" title="Save what is shown as an SVG image" onClick={onSvg}>SVG</button>
      <button title="Save what is shown as a PNG image" onClick={onPng}>PNG</button>
    </div>
  );
}

// A box, the devices beside it, and the boxes it is cabled to.
export function neighbours(data, box) {
  const names = [box, ...data.nodes.filter((n) => n.owner === box).map((n) => n.name)];
  for (const link of data.links) {
    const other = link.a === box ? link.b : link.b === box ? link.a : null;
    if (other && data.nodes.find((n) => n.name === other).kind === "box") names.push(other);
  }
  return names;
}
