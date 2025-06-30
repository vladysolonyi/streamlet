// src/features/flow-board/components/Edge.jsx

import React, { useEffect, useRef, useState } from "react";
import { getSmoothStepPath, getBezierPath, BaseEdge } from "@xyflow/react";
import { useTelemetry } from "../../../contexts/TelemetryContext";

/**
 * AnimatedEdge with scrolling gradient on processing end.
 */
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
  const isProcessing = !!nodeTelemetry[source]?.isProcessing;

  const [animating, setAnimating] = useState(false);
  const prev = useRef(isProcessing);

  useEffect(() => {
    if (prev.current && !isProcessing) {
      setAnimating(true);
    }
    prev.current = isProcessing;
  }, [isProcessing]);

  useEffect(() => {
    if (!animating) return;
    // we'll turn off after 4s (match gradient dur)
    const t = setTimeout(() => setAnimating(false), 4000);
    return () => clearTimeout(t);
  }, [animating]);

  return (
    <g className={`animated-edge${animating ? " is-animating" : ""}`}>
      <defs>
        <linearGradient
          id={`edge-grad-${id}`}
          x1="0%"
          y1="0%"
          x2="100%"
          y2="0%"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="var(--color-secondary)" />
          <stop offset="25%" stopColor="var(--color-primary)" />
          <stop offset="50%" stopColor="var(--color-secondary)" />
          <stop offset="75%" stopColor="var(--color-primary)" />
          <stop offset="100%" stopColor="var(--color-secondary)" />
          <animateTransform
            attributeName="gradientTransform"
            type="translate"
            from="-300,0"
            to="300,0"
            dur="0.3s"
            repeatCount="indefinite"
          />
        </linearGradient>
      </defs>

      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: animating
            ? `url(#edge-grad-${id})`
            : "var(--color-secondary)",
          strokeWidth: 2,
        }}
      />
    </g>
  );
};

/**
 * ReferenceEdge: straight (bezier) edge used for references.
 * Must be registered under edgeTypes.straight
 */
const ReferenceEdge = ({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.5, // you can tweak this
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      className="reference-edge-path"
      style={{
        stroke: "var(--color-info)",
        strokeDasharray: "5 5",
        strokeWidth: 2,
      }}
    />
  );
};

export const DefEdge = (props) => <AnimatedEdge {...props} />;
export const RefEdge = (props) => <ReferenceEdge {...props} />;
