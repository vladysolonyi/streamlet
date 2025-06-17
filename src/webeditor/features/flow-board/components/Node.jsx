import React, { useEffect, useState } from "react";
import { Handle } from "@xyflow/react";
import { useTelemetry } from "../../../contexts/TelemetryContext";

const Node = ({ id, data, selected }) => {
  const { nodeActivity } = useTelemetry();
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    if (nodeActivity[id]) {
      setIsActive(true);
      const timer = setTimeout(() => setIsActive(false), 250);
      return () => clearTimeout(timer);
    }
  }, [nodeActivity[id]]);

  return (
    <div
      className={`status-border-wrapper 
        ${isActive ? "active" : ""} 
        ${selected ? "selected" : ""} 
        green`}
    >
      <div className={`custom-node ${selected ? "selected" : ""}`}>
        <Handle type="target" position="top" />
        <div className="node-header">{data.label}</div>
        <Handle type="source" position="bottom" />
      </div>
    </div>
  );
};

export default Node;
