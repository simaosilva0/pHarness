import { BaseEdge, Position, getSmoothStepPath, useReactFlow } from "@xyflow/react";

// The path of every cable drawn, by id, so a picture of the diagram can be saved.
export const drawn = new Map();

const horizontal = (p) => p === Position.Left || p === Position.Right;

// An orthogonal cable. Its middle run has a grip: drag it to move the run.
export default function CableEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, data }) {
  const { screenToFlowPosition } = useReactFlow();
  const across = horizontal(sourcePosition) && horizontal(targetPosition);   // the middle run is vertical
  const along = !horizontal(sourcePosition) && !horizontal(targetPosition);  // the middle run is horizontal
  const centre = data.center;
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, borderRadius: 8, offset: 18,
    centerX: across && centre !== undefined ? centre : undefined,
    centerY: along && centre !== undefined ? centre : undefined,
  });
  drawn.set(id, path);

  function grab(event) {
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event) {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const at = screenToFlowPosition({ x: event.clientX, y: event.clientY });
    data.setCenter(data.key, Math.round((across ? at.x : at.y) / 10) * 10);
  }

  return (
    <g className="cable">
      <BaseEdge path={path} style={style} interactionWidth={14} />
      {(across || along) && (
        <circle className="grip" cx={across ? centre ?? labelX : labelX} cy={along ? centre ?? labelY : labelY} r={6}
                onPointerDown={grab} onPointerMove={move}
                onDoubleClick={(e) => { e.stopPropagation(); data.setCenter(data.key, undefined); }} />
      )}
    </g>
  );
}
