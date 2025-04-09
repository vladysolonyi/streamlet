import React, { useState, useEffect } from "react";
import { useDnD } from "./DnDContext";

const CATEGORY_CLASS_MAP = {
  exporters: "output",
  loaders: "input",
};

const Sidebar = () => {
  const [_, setType] = useDnD();
  const [nodeTypes, setNodeTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
  }, []);

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
      <div className="description">
        You can drag these nodes to the pane on the right.
      </div>
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
