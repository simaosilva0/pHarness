import { Handle, Position } from "@xyflow/react";
import { SIDES, handleId } from "./routing.js";

const POSITION = { left: Position.Left, right: Position.Right, top: Position.Top, bottom: Position.Bottom };

// A box or a device. Each side has a row of handles, one for every cable that may
// end on the node; they are only seen while a cable end is being moved.
export default function CarNode({ data }) {
  const slots = Math.max(data.cables, 1);
  return (
    <div className={`card ${data.kind}${data.found ? " found" : ""}`} style={{ width: data.w, height: data.h }}>
      <div className="name">{data.name}</div>
      {data.info && <div className="info">{data.info}</div>}
      {SIDES.flatMap((side) =>
        Array.from({ length: slots }, (_, i) => {
          const at = `${((i + 1) / (slots + 1)) * 100}%`;
          const style = side === "left" || side === "right" ? { top: at } : { left: at };
          return <Handle key={handleId(side, i)} id={handleId(side, i)} type="source" position={POSITION[side]} style={style} />;
        }))}
    </div>
  );
}
