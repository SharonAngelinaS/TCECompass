import nodes from "../data/walkNodes.json";
import edges from "../data/walkEdges.json";

export function buildGraph() {
  const graph = {};

  nodes.forEach(n => (graph[n.id] = []));

  edges.forEach(([a, b]) => {
    graph[a].push(b);
    graph[b].push(a);
  });

  return graph;
}
