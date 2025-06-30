import React, { useEffect, useRef, useState } from "react";
import { getSmoothStepPath, BaseEdge } from "@xyflow/react";
import { useTelemetry } from "../../../contexts/TelemetryContext";

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
  const motionRef = useRef(null);

  useEffect(() => {
    if (prev.current && !isProcessing) {
      setAnimating(true);
      motionRef.current?.beginElement();
    }
    prev.current = isProcessing;
  }, [isProcessing]);

  useEffect(() => {
    if (!animating) return;
    const t = setTimeout(() => setAnimating(false), 4000); // match gradient animation
    return () => clearTimeout(t);
  }, [animating]);

  return (
    <g className={`animated-edge${animating ? " is-animating" : ""}`}>
      {/* Define a scrolling gradient */}
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
          {/* animate gradientShift by translating the gradient over time */}
          <animateTransform
            attributeName="gradientTransform"
            type="translate"
            from="-100,0"
            to="100,0"
            dur="0.3s"
            repeatCount="indefinite"
          />
        </linearGradient>
      </defs>

      {/* Edge using either solid color or gradient */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: animating
            ? `url(#edge-grad-${id})`
            : "var(--color-secondary)", // fallback or any static
          strokeWidth: 2,
        }}
      />
    </g>
  );
};

export const DefaultEdge = (props) => <AnimatedEdge {...props} />;
export const ReferenceEdge = (props) => {
  // leave reference-edge unchanged
  const [edgePath] = getSmoothStepPath(props);
  return (
    <BaseEdge
      id={props.id}
      path={edgePath}
      className="reference-edge-path"
      style={{ stroke: "var(--color-info)", strokeDasharray: "5 5" }}
    />
  );
};
