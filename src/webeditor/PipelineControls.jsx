import React, { useState, useEffect } from "react";
import { composeConfig } from "./configUtils";
import { useTelemetry } from "./TelemetryContext"; // Import the telemetry context

const API_KEY = "SECRET_KEY";

const PipelineControls = ({ config }) => {
  const [pipelineId, setPipelineId] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState("not created");
  const [error, setError] = useState(null);
  const { updateNodeActivity } = useTelemetry(); // Get updateNodeActivity from context

  useEffect(() => {
    if (!pipelineId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/telemetry`);

    ws.onopen = () => {
      console.log(`WebSocket connected for pipeline ${pipelineId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Check if this is a telemetry message
        if (data.node_id && data.metric && data.value !== undefined) {
          console.log("Telemetry update:", data);
          // Update telemetry context with the node activity
          updateNodeActivity(data.node_id);
          console.log("Node activity updated:", data.node_id);
        }
        // Check if this is a connection acknowledgement
        else if (data.status === "connection_ack") {
          console.log("Server connection confirmed. Status:", data.status);
        }
        // Handle other message types
        else {
          console.log("Received message:", data);
        }
      } catch (err) {
        console.error("Error parsing message:", err, "Raw data:", event.data);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = (event) => {
      console.log(`Connection closed: ${event.code} - ${event.reason}`);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Component unmounted");
      }
    };
  }, [pipelineId, updateNodeActivity]); // Add updateNodeActivity to dependencies

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
      {/* Removed TelemetryListener since we're handling it directly here */}
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
