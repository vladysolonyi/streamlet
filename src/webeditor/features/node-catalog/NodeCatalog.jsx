import React, { useState } from "react";
import { useDnD } from "../../contexts/DnDContext";

const CATEGORY_LABELS = {
  sources: "sources",
  exporters: "exporters",
  modifiers: "modifiers",
};

const NodeCatalog = () => {
  const { setType, nodeTypes } = useDnD();
  const [openFolders, setOpenFolders] = useState({});

  // Group nodeTypes by category
  const grouped = Object.entries(nodeTypes).reduce((acc, [type, data]) => {
    const cat = data.category || "uncategorized";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push({ type, label: formatName(type) });
    return acc;
  }, {});

  const toggleFolder = (cat) => {
    setOpenFolders((o) => ({ ...o, [cat]: !o[cat] }));
  };

  function onDragStart(e, nodeType) {
    setType(nodeType);
    e.dataTransfer.effectAllowed = "move";
  }

  function formatName(name) {
    return name
      .replace(/_/g, " ")
      .replace(/(^\w|\s\w)/g, (m) => m.toUpperCase());
  }

  if (Object.keys(grouped).length === 0) {
    return (
      <div className="catalog__empty">
        No node types available. Please check your connection.
      </div>
    );
  }

  return (
    <div className="catalog">
      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat} className="catalog__folder">
          <button
            type="button"
            className="catalog__folder-toggle"
            onClick={() => toggleFolder(cat)}
          >
            {openFolders[cat] ? "-" : "+"}{" "}
            {CATEGORY_LABELS[cat] || formatName(cat)}
          </button>
          {openFolders[cat] && (
            <ul className="catalog__list">
              {items.map(({ type, label }) => (
                <li
                  key={type}
                  className="catalog__item"
                  draggable
                  onDragStart={(e) => onDragStart(e, type)}
                >
                  {label}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
};

export default NodeCatalog;
