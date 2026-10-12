import { BaseEdge, getSmoothStepPath } from "@xyflow/react";

// The path of every cable drawn, by id, so a picture of the diagram can be saved.
export const drawn = new Map();

// An orthogonal cable.
export default function CableEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style }) {
  const [path] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, borderRadius: 8, offset: 18,
  });
  drawn.set(id, path);
  return <BaseEdge path={path} style={style} interactionWidth={14} />;
}
