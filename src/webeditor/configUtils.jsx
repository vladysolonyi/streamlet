import { v4 as uuid } from "uuid";

export const parseConfig = (config, nodeTypes = {}) => {
  // Add default parameter
  // Validate all nodes have unique names
  const names = new Set();
  config.nodes.forEach((node) => {
    if (names.has(node.name)) {
      throw new Error(`Duplicate node name: ${node.name}`);
    }
    names.add(node.name);
  });

  const initialNodes = config.nodes.map((node, index) => {
    const nodeSchema = nodeTypes[node.type]?.params_schema || {}; // Safe access

    return {
      id: node.name,
      type: node.type,
      position: { x: index * 250, y: 0 },
      data: {
        label: node.name,
        params: {
          ...Object.fromEntries(
            Object.entries(nodeSchema.properties || {}).map(([key, def]) => [
              key,
              def?.default,
            ]) // Added safe navigation
          ),
          ...(node.params || {}),
        },
        paramsSchema: nodeSchema,
      },
    };
  });

  const initialEdges = [];
  config.nodes.forEach((node) => {
    node.inputs?.forEach((inputName) => {
      initialEdges.push({
        id: `${inputName}-to-${node.name}-${uuid()}`,
        source: inputName,
        target: node.name,
      });
    });
  });

  return { initialNodes, initialEdges };
};

// composeConfig remains the same
export const composeConfig = (nodes, edges) => ({
  nodes: nodes.map((node) => ({
    type: node.type,
    name: node.data.label,
    params: node.data.params,
    inputs: edges
      .filter((edge) => edge.target === node.id)
      .map((edge) => edge.source),
  })),
});
