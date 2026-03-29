import places from "../data/places.json";
import nodes from "../data/walkNodes.json";

/* distance between two lat/lng points in meters */
function distance(a, b) {
  const R = 6371000;
  const toRad = x => x * Math.PI / 180;

  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);

  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) *
      Math.cos(toRad(b.lat)) *
      Math.sin(dLng / 2) ** 2;

  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

/* returns { placeId : nodeId } */
export function mapPlacesToNodes() {
  const mapping = {};

  places.forEach(place => {
    let bestNode = null;
    let bestDist = Infinity;

    nodes.forEach(node => {
      const d = distance(place, node);
      if (d < bestDist) {
        bestDist = d;
        bestNode = node.id;
      }
    });

    mapping[place.id] = bestNode;
  });

  return mapping;
}