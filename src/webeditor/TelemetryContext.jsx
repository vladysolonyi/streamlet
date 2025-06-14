import { createContext, useContext, useState, useEffect } from "react";

const TelemetryContext = createContext();

export const TelemetryProvider = ({ children }) => {
  const [nodeActivity, setNodeActivity] = useState({});

  const updateNodeActivity = (nodeId) => {
    setNodeActivity((prev) => ({
      ...prev,
      [nodeId]: Date.now(),
    }));
  };

  return (
    <TelemetryContext.Provider value={{ nodeActivity, updateNodeActivity }}>
      {children}
    </TelemetryContext.Provider>
  );
};

export const useTelemetry = () => useContext(TelemetryContext);
