import { drawn } from "./CableEdge.jsx";

const xml = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// What is shown as a standalone SVG on white: the shown nodes and, when cables
// are on, the cables between them. `nodes` have positions in `x`, `y`.
export function svgOf(nodes, edges, withCables) {
  if (!nodes.length) return null;
  const pad = 40;
  const x0 = Math.min(...nodes.map((n) => n.x)) - pad, y0 = Math.min(...nodes.map((n) => n.y)) - pad;
  const w = Math.max(...nodes.map((n) => n.x + n.w)) + pad - x0, h = Math.max(...nodes.map((n) => n.y + n.h)) + pad - y0;
  const out = [`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${x0} ${y0} ${w} ${h}" font-family="system-ui, sans-serif">`,
    `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="#ffffff"/>`];
  if (withCables) {
    for (const edge of edges) {
      const d = drawn.get(edge.id);
      if (d) out.push(`<path d="${d}" fill="none" stroke="#6a6f78" stroke-width="${edge.style.strokeWidth}" stroke-linejoin="round"/>`);
    }
  }
  for (const n of nodes) {
    const box = n.kind === "box";
    out.push(`<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="10" fill="${box ? "#f3f4f6" : "#ffffff"}" stroke="${box ? "#1d1f23" : "#6a6f78"}" stroke-width="${box ? 2 : 1.5}"/>`);
    out.push(`<text x="${n.x + n.w / 2}" y="${n.y + n.h / 2 + (box ? -2 : 4)}" text-anchor="middle" fill="#1d1f23" font-size="${box ? 14 : 12}" font-weight="${box ? 600 : 500}">${xml(n.name)}</text>`);
    if (n.info) out.push(`<text x="${n.x + n.w / 2}" y="${n.y + n.h / 2 + 16}" text-anchor="middle" fill="#6a6f78" font-size="11">${xml(n.info)}</text>`);
  }
  out.push("</svg>");
  return { text: out.join("\n"), width: w, height: h };
}

function download(name, blob) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function fileName(ext) {
  const car = document.title.replace(/ pinout$/, "").replace(/[^A-Za-z0-9._-]+/g, "-") || "car";
  return `${car}-car.${ext}`;
}

export function saveSvg(image) {
  if (image) download(fileName("svg"), new Blob([image.text], { type: "image/svg+xml" }));
}

export function savePng(image) {
  if (!image) return;
  const scale = Math.min(2, 8000 / Math.max(image.width, image.height));
  const picture = new Image();
  picture.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(image.width * scale);
    canvas.height = Math.round(image.height * scale);
    canvas.getContext("2d").drawImage(picture, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => blob && download(fileName("png"), blob), "image/png");
  };
  picture.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(image.text);
}
