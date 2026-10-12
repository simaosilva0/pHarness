// Where each cable leaves each box or device: a side, and a slot on that side.
// Every side has a handle for each cable that may end there (CarNode), so cables
// on one side do not run on top of each other.

export const SIDES = ["left", "right", "top", "bottom"];

export function handleId(side, slot) {
  return `${side}-${slot}`;
}

export function sideOf(id) {
  return id.split("-")[0];
}

// The side of a node facing another: side by side, left or right; one above the
// other, top or bottom.
function facing(a, b) {
  if (a.x + a.w <= b.x) return "right";
  if (b.x + b.w <= a.x) return "left";
  return a.y < b.y ? "bottom" : "top";
}

// A handle for each cable of the item, from where the nodes are now. Cables on a
// side are ordered by where their other end is, so they do not cross; an end the
// user moved (`setup[key].s` or `.t`) stays where they put it.
export function plan(items, positions, setup) {
  const ends = {};
  const found = items.map((item, i) => {
    const a = positions[item.a], b = positions[item.b];
    const mine = setup[item.key] || {};
    const sa = mine.s ? sideOf(mine.s) : facing(a, b);
    const sb = mine.t ? sideOf(mine.t) : facing(b, a);
    if (!mine.s) (ends[item.a + sa] ||= []).push({ i, end: "s", other: b, side: sa });
    if (!mine.t) (ends[item.b + sb] ||= []).push({ i, end: "t", other: a, side: sb });
    return { item, s: mine.s || null, t: mine.t || null, sa, sb };
  });
  for (const group of Object.values(ends)) {
    const vertical = group[0].side === "left" || group[0].side === "right";
    group.sort((p, q) => (vertical ? p.other.y - q.other.y : p.other.x - q.other.x));
    group.forEach((entry, slot) => {
      const one = found[entry.i];
      one[entry.end] = handleId(entry.side, slot);
    });
  }
  return found;
}
