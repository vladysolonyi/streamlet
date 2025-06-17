import { createContext, useContext, useState, useCallback } from "react";

const TelemetryContext = createContext();

export const TelemetryProvider = ({ children }) => {
  const [nodeTelemetry, setNodeTelemetry] = useState({});

  const updateTelemetry = useCallback((nodeId, eventType, data = {}) => {
    setNodeTelemetry((prev) => {
      const now = Date.now();
      const nodeData = prev[nodeId] || {};

      let newState = { ...nodeData };

      switch (eventType) {
        case "processing_start":
          newState = {
            ...newState,
            processingStart: now,
            isProcessing: true,
            error: null,
            rejected: null,
          };
          break;

        case "processing_end":
          newState = {
            ...newState,
            processingEnd: now,
            isProcessing: false,
            error: null,
            rejected: null,
          };
          break;

        case "processing_error":
          newState = {
            ...newState,
            isProcessing: false,
            error: {
              timestamp: now,
              message: data.message || "Error occurred",
            },
          };
          break;

        case "data_rejected":
          newState = {
            ...newState,
            rejected: {
              timestamp: now,
              count: data.count || 1,
              reason: data.reason || "Data rejected",
            },
          };
          break;

        default:
          console.warn("Unknown telemetry event:", eventType);
          break;
      }

      return {
        ...prev,
        [nodeId]: newState,
      };
    });
  }, []);

  return (
    <TelemetryContext.Provider value={{ nodeTelemetry, updateTelemetry }}>
      {children}
    </TelemetryContext.Provider>
  );
};

export const useTelemetry = () => useContext(TelemetryContext);
