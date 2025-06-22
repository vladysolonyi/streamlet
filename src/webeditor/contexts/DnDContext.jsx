import { createContext, useContext, useState, useEffect } from "react";

export const DnDContext = createContext();

export const DnDProvider = ({ children }) => {
  const [nodeTypes, setNodeTypes] = useState({});
  const [type, setType] = useState(null);

  // Load node types from localStorage on initial load
  useEffect(() => {
    const storedNodeTypes = localStorage.getItem("nodeTypes");
    if (storedNodeTypes) {
      try {
        setNodeTypes(JSON.parse(storedNodeTypes));
      } catch (error) {
        console.error("Error parsing stored node types:", error);
      }
    }
  }, []);

  // Save node types to localStorage whenever they change
  useEffect(() => {
    if (Object.keys(nodeTypes).length > 0) {
      localStorage.setItem("nodeTypes", JSON.stringify(nodeTypes));
    }
  }, [nodeTypes]);

  // Fetch node types from server (if not already loaded)
  useEffect(() => {
    if (Object.keys(nodeTypes).length === 0) {
      fetchNodeTypes();
    }

    async function fetchNodeTypes() {
      try {
        const response = await fetch("http://localhost:8000/node-types");
        const types = await response.json();
        setNodeTypes(types);
      } catch (error) {
        console.error("Failed to fetch node types:", error);
        // Use empty types - we'll try to load from localStorage instead
      }
    }
  }, []);

  return (
    <DnDContext.Provider
      value={{
        type,
        setType,
        nodeTypes,
        setNodeTypes, // Add this to the context value
      }}
    >
      {children}
    </DnDContext.Provider>
  );
};

export const useDnD = () => useContext(DnDContext);
