import { createContext, useContext, useState, useCallback } from "react";

const TelemetryContext = createContext();

export const TelemetryProvider = ({ children }) => {
  const [nodeActivity, setNodeActivity] = useState({});

  // Memoize the update function to prevent unnecessary re-renders
  const updateNodeActivity = useCallback((nodeId) => {
    setNodeActivity((prev) => ({
      ...prev,
      [nodeId]: Date.now(),
    }));
  }, []);

  return (
    <TelemetryContext.Provider value={{ nodeActivity, updateNodeActivity }}>
      {children}
    </TelemetryContext.Provider>
  );
};

export const useTelemetry = () => useContext(TelemetryContext);
