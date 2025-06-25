import { v4 as uuid } from "uuid";

// Helper to extract references from parameters
export const extractReferences = (params) => {
  const references = [];

  const traverse = (obj, path = []) => {
    for (const [key, value] of Object.entries(obj)) {
      const currentPath = [...path, key];

      if (typeof value === "string" && value.startsWith("@ref:")) {
        const refParts = value.substring(5).split(".");
        if (refParts.length > 0) {
          references.push({
            sourceNode: refParts[0],
            path: currentPath.join("."),
            refValue: value,
          });
        }
      } else if (typeof value === "object" && value !== null) {
        traverse(value, currentPath);
      }
    }
  };

  traverse(params);
  return references;
};

export const validateConfig = (config) => {
  // Basic validation logic
  if (!config) throw new Error("Config is undefined");
  if (!config.nodes) throw new Error("Config missing nodes array");
};

export const parseConfig = (config, nodeTypes = {}) => {
  validateConfig(config);

  const names = new Set();
  config.nodes.forEach((node) => {
    if (names.has(node.name)) {
      throw new Error(`Duplicate node name: ${node.name}`);
    }
    names.add(node.name);
  });

  const initialNodes = config.nodes.map((node, index) => {
    const nodeSchema = nodeTypes[node.type]?.params_schema || {};
    return {
      id: node.name,
      type: node.type,
      position: node.position || { x: index * 250, y: 0 },
      data: {
        label: node.name,
        params: {
          ...Object.fromEntries(
            Object.entries(nodeSchema.properties || {}).map(([key, def]) => [
              key,
              def?.default,
            ])
          ),
          ...(node.params || {}),
        },
        paramsSchema: nodeSchema,
        references: extractReferences(node.params || {}),
      },
    };
  });

  const initialEdges = [];

  // Create standard input edges
  config.nodes.forEach((node) => {
    node.inputs?.forEach((inputName) => {
      initialEdges.push({
        id: `${inputName}-to-${node.name}-${uuid()}`,
        source: inputName,
        target: node.name,
      });
    });
  });

  // Create reference edges
  config.nodes.forEach((node) => {
    const references = extractReferences(node.params || {});
    references.forEach((ref) => {
      initialEdges.push({
        id: `ref-${ref.sourceNode}-${node.name}-${uuid()}`,
        source: ref.sourceNode,
        target: node.name,
        type: "straight",
        className: "reference-edge",
        animated: true,
        data: {
          referencePath: ref.path,
          refValue: ref.refValue,
        },
      });
    });
  });

  return { initialNodes, initialEdges };
};

export const composeConfig = (nodes, edges) => {
  // Get FPS limit from localStorage
  const fpsLimit = parseInt(localStorage.getItem("fps_limit") || 60);

  return {
    settings: {
      fps_limit: fpsLimit,
    },
    nodes: nodes.map((node) => ({
      id: node.id,
      type: node.type,
      name: node.data.label,
      position: node.position,
      params: node.data.params,
      inputs: edges
        .filter((edge) => edge.target === node.id && edge.type !== "straight")
        .map((edge) => edge.source),
    })),
  };
};

export const getEmptyConfig = () => ({
  settings: {
    fps_limit: 60, // Default FPS limit
  },
  nodes: [],
});
