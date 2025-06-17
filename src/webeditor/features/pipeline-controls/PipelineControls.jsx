import React, { useState, useEffect } from "react";
import { useTelemetry } from "../../contexts/TelemetryContext";
import { webSocketService } from "../../services/websocket";

const API_KEY = "SECRET_KEY";

const PipelineControls = ({ config }) => {
  const [pipelineId, setPipelineId] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState("not created");
  const [error, setError] = useState(null);
  const { updateTelemetry } = useTelemetry();

  useEffect(() => {
    if (!pipelineId) return;

    webSocketService.connect(pipelineId);

    // Add listener for WebSocket messages
    const removeListener = webSocketService.addListener((data) => {
      // Handle different telemetry metrics
      switch (data.metric) {
        case "processing_start":
          updateTelemetry(data.node_id, "processing_start");
          break;
        case "processing_end":
          updateTelemetry(data.node_id, "processing_end");
          break;
        case "processing_error":
          updateTelemetry(data.node_id, "processing_error", {
            message: data.value || "Error occurred",
          });
          break;
        case "data_rejected":
          updateTelemetry(data.node_id, "data_rejected", {
            count: data.value || 1,
          });
          break;
        default:
          // Ignore other metrics like execution_time
          break;
      }
    });

    return () => {
      removeListener();
      webSocketService.disconnect();
    };
  }, [pipelineId, updateTelemetry]);

  const handleInitialize = async () => {
    try {
      const pipelineConfig = {
        config: config,
        name: "Demo Pipeline",
      };

      const response = await fetch("http://localhost:8000/pipelines", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify(pipelineConfig),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to initialize pipeline");
      }

      console.log("Pipeline initialized successfully:", data);
      setPipelineId(data.id);
      setPipelineStatus("created");
    } catch (err) {
      console.error("Initialize error:", err);
      setError(err.message);
      setPipelineStatus("error");
    }
  };

  const handleStart = async () => {
    if (!pipelineId) return;

    try {
      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}/start`,
        {
          method: "POST",
          headers: {
            "X-API-Key": API_KEY,
          },
        }
      );

      await response.json();
      setPipelineStatus("running");
      console.log("Pipeline started successfully", response);
    } catch (err) {
      console.error("Start error:", err);
      setError(err.message);
    }
  };

  const handleStop = async () => {
    if (!pipelineId) return;

    try {
      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}/stop`,
        {
          method: "POST",
          headers: {
            "X-API-Key": API_KEY,
          },
        }
      );

      await response.json();
      setPipelineStatus("stopped");
      console.log("Pipeline stopped successfully", response);
    } catch (err) {
      console.error("Stop error:", err);
      setError(err.message);
    }
  };

  return (
    <div className="pipeline-controls">
      {error && <div className="error-message">{error}</div>}
      <button
        onClick={handleInitialize}
        disabled={pipelineStatus !== "not created"}
      >
        Initialize Pipeline
      </button>
      <button
        onClick={handleStart}
        disabled={!pipelineId || pipelineStatus === "running"}
      >
        Start Pipeline
      </button>
      <button
        onClick={handleStop}
        disabled={!pipelineId || pipelineStatus !== "running"}
      >
        Stop Pipeline
      </button>
      <div className="pipeline-status">Pipeline Status: {pipelineStatus}</div>
    </div>
  );
};

export default PipelineControls;
