// src/components/FpsDisplay.jsx
import React, { useState, useEffect } from "react";
import { usePipeline } from "../../contexts/PipelineContext";
import { webSocketService } from "../../services/websocket";

const FpsDisplay = () => {
  const { pipelineId, pipelineStatus } = usePipeline();
  const [currentFps, setCurrentFps] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(Date.now());

  useEffect(() => {
    if (!pipelineId || pipelineStatus !== "running") return;

    const handleFpsUpdate = (data) => {
      if (data.metric === "fps") {
        setCurrentFps(data.value);
        setLastUpdated(Date.now());
      }
    };

    const removeListener = webSocketService.addListener(handleFpsUpdate);
    return () => removeListener();
  }, [pipelineId, pipelineStatus]);

  const isStale =
    pipelineStatus === "running" && Date.now() - lastUpdated > 3000;

  return (
    <div className="fps-display--bar">
      <span className="fps-value">
        {isStale ? "—" : currentFps.toFixed(1)}
        <small className="fps-unit">fps</small>
      </span>
    </div>
  );
};

export default FpsDisplay;
