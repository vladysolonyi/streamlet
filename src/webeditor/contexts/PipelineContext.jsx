// contexts/PipelineContext.js
import { createContext, useContext, useState, useCallback } from "react";

const PipelineContext = createContext();

export const PipelineProvider = ({ children }) => {
  const [pipelineId, setPipelineId] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState("not created");
  const [hasChanges, setHasChanges] = useState(false);
  const [autoUpdate, setAutoUpdate] = useState(false);
  const [lastAppliedConfig, setLastAppliedConfig] = useState(null);
  const [error, setError] = useState(null);

  // Reset all state
  const resetPipeline = useCallback(() => {
    setPipelineId(null);
    setPipelineStatus("not created");
    setHasChanges(false);
    setAutoUpdate(false);
    setLastAppliedConfig(null);
    setError(null);
  }, []);

  return (
    <PipelineContext.Provider
      value={{
        pipelineId,
        setPipelineId,
        pipelineStatus,
        setPipelineStatus,
        hasChanges,
        setHasChanges,
        autoUpdate,
        setAutoUpdate,
        lastAppliedConfig,
        setLastAppliedConfig,
        error,
        setError,
        resetPipeline,
      }}
    >
      {children}
    </PipelineContext.Provider>
  );
};

export const usePipeline = () => useContext(PipelineContext);
