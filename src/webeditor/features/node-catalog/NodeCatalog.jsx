import React from "react";
import { useDnD } from "../../contexts/DnDContext";

const CATEGORY_CLASS_MAP = {
  exporters: "output",
  loaders: "input",
};

const NodeCatalog = () => {
  const { setType, nodeTypes } = useDnD(); // Removed setNodeTypes

  const onDragStart = (event, nodeType) => {
    setType(nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  const formatName = (name) => {
    return name
      .replace(/_/g, " ")
      .replace(/(^\w|\s\w)/g, (m) => m.toUpperCase());
  };

  // No loading state needed - nodeTypes come from context
  if (Object.keys(nodeTypes).length === 0) {
    return <div>No node types available. Please check your connection.</div>;
  }

  return (
    <>
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
    </>
  );
};

export default NodeCatalog;
