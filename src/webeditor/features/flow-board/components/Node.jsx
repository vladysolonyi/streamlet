import React, { useState, useEffect, useRef } from "react";
import { Handle } from "@xyflow/react";
import { useTelemetry } from "../../../contexts/TelemetryContext";

const MIN_PROCESSING_DURATION = 100; // Minimum display time in ms

const Node = ({ id, data, selected }) => {
  const { nodeTelemetry } = useTelemetry();
  const nodeData = nodeTelemetry[id] || {};
  const [showProcessing, setShowProcessing] = useState(false);
  const processingTimer = useRef(null);
  const processingStartTime = useRef(0);

  // Handle processing state with minimum duration
  useEffect(() => {
    // Clear any existing timers
    if (processingTimer.current) {
      clearTimeout(processingTimer.current);
      processingTimer.current = null;
    }

    if (nodeData.isProcessing) {
      // Start processing visualization
      setShowProcessing(true);
      processingStartTime.current = Date.now();
    } else if (showProcessing) {
      // Calculate remaining time for minimum duration
      const elapsed = Date.now() - processingStartTime.current;
      const remaining = MIN_PROCESSING_DURATION - elapsed;

      if (remaining > 0) {
        // If processing ended too soon, maintain visualization for remaining time
        processingTimer.current = setTimeout(() => {
          setShowProcessing(false);
        }, remaining);
      } else {
        // If minimum duration already met, hide immediately
        setShowProcessing(false);
      }
    }

    return () => {
      if (processingTimer.current) {
        clearTimeout(processingTimer.current);
      }
    };
  }, [nodeData.isProcessing, showProcessing]);

  return (
    <div
      className={`
      status-border-wrapper 
      ${showProcessing ? "processing" : ""}
      ${nodeData.error ? "error" : ""}
      ${nodeData.rejected ? "rejected" : ""}
      ${selected ? "selected" : ""}
    `}
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
