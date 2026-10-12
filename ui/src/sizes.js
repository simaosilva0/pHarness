// How big a box or device is: as the layout left it, or bigger when its name
// needs more room at the text size chosen.

const NAME = { box: { px: 20, weight: 600 }, device: { px: 14, weight: 500 } };
const PAD_X = 24, PAD_Y = 12, INFO = 22;   // room around the name, and for the stats line a box shows when pointed at

let canvas;
function width(text, font) {
  canvas ||= document.createElement("canvas");
  const context = canvas.getContext("2d");
  context.font = font;
  return context.measureText(text).width;
}

export function sizeOf(node, grid, scale) {
  const { px, weight } = NAME[node.kind];
  const size = px * scale;
  const font = `${weight} ${size}px system-ui, sans-serif`;
  const w = Math.max(node.w * grid, Math.ceil(width(node.name, font) + 2 * PAD_X));
  const room = Math.ceil(size * 1.15) + 2 * PAD_Y + (node.kind === "box" && node.info ? 2 * INFO : 0);
  return { w, h: Math.max(node.h * grid, room) };
}
