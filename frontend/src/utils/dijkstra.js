export function shortestPath(graph, start, end) {
  const dist = {};
  const prev = {};
  const Q = new Set(Object.keys(graph));

  Object.keys(graph).forEach(n => (dist[n] = Infinity));
  dist[start] = 0;

  while (Q.size) {
    let u = [...Q].reduce((a, b) => (dist[a] < dist[b] ? a : b));
    Q.delete(u);

    if (u === end) break;

    graph[u].forEach(v => {
      const alt = dist[u] + 1;
      if (alt < dist[v]) {
        dist[v] = alt;
        prev[v] = u;
      }
    });
  }

  const path = [];
  let cur = end;

  while (cur) {
    path.unshift(cur);
    cur = prev[cur];
  }

  return path;
}