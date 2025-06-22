import { useEffect, useRef } from "react";
import { extractReferences } from "../utils/configUtils";

export const useReferenceMonitor = (nodes, setEdges) => {
  // Use ref to track previous references
  const prevReferences = useRef(new Map());

  useEffect(() => {
    // Create a map of all current reference edges
    const currentEdgesMap = new Map();
    setEdges((edges) => {
      edges.forEach((edge) => {
        if (edge.type === "straight" && edge.data) {
          const key = `${edge.source}-${edge.target}-${edge.data.referencePath}`;
          currentEdgesMap.set(key, edge);
        }
      });
      return edges;
    });

    // Collect all current references from nodes
    const currentReferences = new Map();
    nodes.forEach((node) => {
      const references = extractReferences(node.data.params || {});
      references.forEach((ref) => {
        const key = `${ref.sourceNode}-${node.id}-${ref.path}`;
        currentReferences.set(key, {
          source: ref.sourceNode,
          target: node.id,
          path: ref.path,
          refValue: ref.refValue,
        });
      });
    });

    // Check if references have actually changed
    let referencesChanged = false;

    // Check for new or modified references
    for (const [key, ref] of currentReferences) {
      if (!prevReferences.current.has(key)) {
        referencesChanged = true;
        break;
      }
    }

    // Check for removed references
    if (!referencesChanged) {
      for (const key of prevReferences.current.keys()) {
        if (!currentReferences.has(key)) {
          referencesChanged = true;
          break;
        }
      }
    }

    // Only update edges if references changed
    if (referencesChanged) {
      const newRefEdges = [];

      // Create new edges for all current references
      currentReferences.forEach((ref, key) => {
        // Only create if doesn't exist or changed
        if (!currentEdgesMap.has(key)) {
          newRefEdges.push({
            id: `ref-${key}-${Date.now()}`,
            source: ref.source,
            target: ref.target,
            type: "straight",
            className: "reference-edge",
            animated: true,
            data: {
              referencePath: ref.path,
              refValue: ref.refValue,
            },
          });
        }
      });

      // Update edges
      setEdges((edges) => {
        // Filter out old reference edges
        const filtered = edges.filter(
          (edge) => !(edge.type === "straight" && edge.data)
        );

        // Add new reference edges
        return [...filtered, ...newRefEdges];
      });

      // Update previous references
      prevReferences.current = currentReferences;
    }
  }, [nodes, setEdges]); // Only run when nodes change
};

export default useReferenceMonitor;
