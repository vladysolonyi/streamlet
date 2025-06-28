import React, { useEffect, useRef, useState } from "react";
import { getSmoothStepPath, BaseEdge } from "@xyflow/react";
import { useTelemetry } from "../../../contexts/TelemetryContext";

// Core animated edge: black idle, green while animating, beam circle runs on processing end
const AnimatedEdge = ({
  id,
  source,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
}) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const { nodeTelemetry } = useTelemetry();
  const isProcessing = nodeTelemetry[source]?.isProcessing;
  const [animating, setAnimating] = useState(false);
  const prevProcessing = useRef(isProcessing);
  const animateRef = useRef(null);
  const ANIM_DURATION_MS = 300;

  // Trigger beam animation on processing end
  useEffect(() => {
    if (prevProcessing.current && !isProcessing) {
      setAnimating(true);
      animateRef.current?.beginElement();
    }
    prevProcessing.current = isProcessing;
  }, [isProcessing]);

  // Reset animating state after duration
  useEffect(() => {
    let timeout;
    if (animating) {
      timeout = setTimeout(() => setAnimating(false), ANIM_DURATION_MS);
    }
    return () => clearTimeout(timeout);
  }, [animating]);

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: animating ? "rgb(0, 255, 171)" : "#000",
          strokeWidth: 2,
        }}
      />
      <circle r="5" fill="#00ffab" style={{ opacity: animating ? 1 : 0 }}>
        <animateMotion
          ref={animateRef}
          begin="indefinite"
          dur="0.3s"
          calcMode="spline"
          keyTimes="0;1"
          keySplines=".4 0 .6 1"
          path={edgePath}
        />
      </circle>
    </>
  );
};

// Preserve original edge exports
export const DefaultEdge = (props) => <AnimatedEdge {...props} />;
export const ReferenceEdge = (props) => <AnimatedEdge {...props} />;
