import { v4 as uuid } from "uuid";

export const validateConfig = (config) => {
  if (!config || typeof config !== "object") {
    throw new Error("Invalid config format: must be an object");
  }

  if (!Array.isArray(config.nodes)) {
    throw new Error("Config must contain a nodes array");
  }

  const names = new Set();
  for (const node of config.nodes) {
    if (!node.type || typeof node.type !== "string") {
      throw new Error(`Node missing type property: ${JSON.stringify(node)}`);
    }
    if (!node.name || typeof node.name !== "string") {
      throw new Error(`Node missing name property: ${JSON.stringify(node)}`);
    }
    if (names.has(node.name)) {
      throw new Error(`Duplicate node name: ${node.name}`);
    }
    names.add(node.name);
  }

  return true;
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
      position: { x: index * 250, y: 0 },
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
