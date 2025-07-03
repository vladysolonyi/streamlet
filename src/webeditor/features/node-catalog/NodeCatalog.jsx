import React, { useState } from "react";
import { useDnD } from "../../contexts/DnDContext";

// Define both order and labels in one structure
const CATEGORIES = [
  { id: "sources", label: "Sources" },
  { id: "modifiers", label: "Modifiers" },
  { id: "exporters", label: "Exporters" },
];

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

  // Create lookup map for labels
  const categoryLabels = CATEGORIES.reduce((map, cat) => {
    map[cat.id] = cat.label;
    return map;
  }, {});

  // Create ordered categories list
  const orderedCategories = [
    ...CATEGORIES.map((cat) => cat.id),
    ...Object.keys(grouped).filter(
      (id) => !CATEGORIES.some((c) => c.id === id)
    ),
  ];

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
      {orderedCategories.map(
        (cat) =>
          grouped[cat] && (
            <div key={cat} className="catalog__folder">
              <button
                type="button"
                className="catalog__folder-toggle"
                onClick={() => toggleFolder(cat)}
              >
                {openFolders[cat] ? "-" : "+"}{" "}
                {categoryLabels[cat] || formatName(cat)}
              </button>
              {openFolders[cat] && (
                <ul className="catalog__list">
                  {grouped[cat].map(({ type, label }) => (
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
          )
      )}
    </div>
  );
};

export default NodeCatalog;
