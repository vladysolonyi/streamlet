import React, { useState, useEffect } from "react";
import { usePipeline } from "../../contexts/PipelineContext";
import { useDebugConsole } from "../../contexts/DebugConsoleContext";
import { webSocketService } from "../../services/websocket";

const FpsControl = () => {
  const { pipelineId, pipelineStatus, lastAppliedConfig } = usePipeline();
  const { addMessage } = useDebugConsole();
  const [fpsLimit, setFpsLimit] = useState(60);
  const [currentFps, setCurrentFps] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(Date.now());

  // Load saved FPS limit from localStorage
  useEffect(() => {
    const savedFps = localStorage.getItem("fps_limit");
    if (savedFps) {
      try {
        const value = parseInt(savedFps);
        setFpsLimit(isNaN(value) ? 60 : value);
      } catch {
        setFpsLimit(60);
      }
    }
  }, []);

  // Save FPS limit to localStorage
  useEffect(() => {
    localStorage.setItem("fps_limit", fpsLimit.toString());
  }, [fpsLimit]);

  // Real FPS telemetry from backend
  useEffect(() => {
    if (!pipelineId || pipelineStatus !== "running") return;

    const handleFpsUpdate = (data) => {
      // Handle new telemetry format
      if (data.metric === "fps") {
        setCurrentFps(data.value);
        setLastUpdated(Date.now());
      }
    };

    const removeListener = webSocketService.addListener(handleFpsUpdate);

    return () => {
      removeListener();
    };
  }, [pipelineStatus, pipelineId]);

  const handleFpsChange = (e) => {
    const value = parseInt(e.target.value);
    const newValue = isNaN(value) ? 60 : Math.min(240, Math.max(1, value));
    setFpsLimit(newValue);
    addMessage(`FPS limit set to: ${newValue}`, "info");
  };

  const isStale =
    pipelineStatus === "running" && Date.now() - lastUpdated > 3000;

  return (
    <div className="fps-control">
      <div className="fps-input-group">
        <label htmlFor="fps-limit">FPS Limit:</label>
        <input
          id="fps-limit"
          type="number"
          min="1"
          max="240"
          value={fpsLimit}
          onChange={handleFpsChange}
          disabled={pipelineStatus !== "not created"}
        />
      </div>

      {pipelineStatus === "running" && (
        <div className="fps-display">
          <div className="fps-value">
            {isStale ? "─" : currentFps.toFixed(1)}
            <span className="fps-unit">fps</span>
          </div>
          <div className="fps-limit">
            (Target: {lastAppliedConfig?.settings?.fps_limit || fpsLimit})
          </div>
        </div>
      )}
    </div>
  );
};

export default FpsControl;
