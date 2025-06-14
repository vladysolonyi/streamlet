import React, { useState, useEffect } from "react"; // Add useState import
import { useDnD } from "./DnDContext";

const CATEGORY_CLASS_MAP = {
  exporters: "output",
  loaders: "input",
};

const Sidebar = () => {
  const { setType, nodeTypes, setNodeTypes } = useDnD();
  const [loading, setLoading] = useState(true); // Now using imported useState
  const [error, setError] = useState(null); // Now using imported useState

  useEffect(() => {
    fetch("http://localhost:8000/node-types")
      .then((response) => response.json())
      .then((data) => {
        setNodeTypes(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [setNodeTypes]);

  const onDragStart = (event, nodeType) => {
    setType(nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  const formatName = (name) => {
    return name
      .replace(/_/g, " ")
      .replace(/(^\w|\s\w)/g, (m) => m.toUpperCase());
  };

  if (loading) return <aside>Loading node types...</aside>;
  if (error) return <aside>Error: {error}</aside>;

  return (
    <aside>
      {Object.entries(nodeTypes).map(([nodeType, data]) => (
        <div
          key={nodeType}
          className={`dndnode ${CATEGORY_CLASS_MAP[data.category] || ""} ${
            data.category
          }`}
          onDragStart={(e) => onDragStart(e, nodeType)}
          draggable
        >
          {formatName(nodeType)}
        </div>
      ))}
    </aside>
  );
};

export default Sidebar;
