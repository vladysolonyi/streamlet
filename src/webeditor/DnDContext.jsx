import { createContext, useContext, useState } from "react";

const DnDContext = createContext({
  type: null,
  nodeTypes: {}, // Add nodeTypes to context
  setType: () => {},
  setNodeTypes: () => {},
});

export const DnDProvider = ({ children }) => {
  const [type, setType] = useState(null);
  const [nodeTypes, setNodeTypes] = useState({}); // Initialize nodeTypes state

  return (
    <DnDContext.Provider
      value={{
        type,
        setType,
        nodeTypes, // Provide nodeTypes
        setNodeTypes,
      }}
    >
      {children}
    </DnDContext.Provider>
  );
};

export const useDnD = () => useContext(DnDContext);
