import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useRef, useState } from "react";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import places from "../../../data/places.json";
import nodes from "../../../data/walkNodes.json";
import { buildEdges, nearest, dijkstra } from "../utils/graph";
import "../styles/ExploreTceMap.css";

const edges = buildEdges(nodes);

/** Min seconds between live route recalculations */
const LIVE_REROUTE_MIN_MS = 5000;
/** Min meters moved before re-routing (reduces jitter) */
const LIVE_REROUTE_MIN_M = 12;

const MY_LOCATION = "My location";

function haversineMeters(a, b) {
  const R = 6371000;
  const toRad = (x) => (x * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

function buildRouteFromPoints(fromPoint, toPlace, fromLabel) {
  const s = nearest(fromPoint, nodes);
  const e = nearest(toPlace, nodes);
  const p = dijkstra(s, e, nodes, edges);
  const coords = [
    [fromPoint.lat, fromPoint.lng],
    ...p.map((id) => {
      const n = nodes.find((x) => x.id === id);
      return [n.lat, n.lng];
    }),
    [toPlace.lat, toPlace.lng],
  ];
  return {
    fromName: fromLabel,
    toName: toPlace.name,
    coords,
    start: [fromPoint.lat, fromPoint.lng],
    end: [toPlace.lat, toPlace.lng],
  };
}

const LIBRARY_IMG = "/images/navigation/library.png";
const MAIN_BUILDING_IMG = "/images/navigation/main-building.png";
const FOOD_COURT_IMG = "/images/navigation/food-court.png";
const IT_DEPARTMENT_IMG = "/images/navigation/it-department.png";

const defaultPinIcon = new L.Icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  shadowSize: [41, 41],
});

const PHOTO_PIN = 56;

function photoMarkerIcon(imageSrc) {
  return L.divIcon({
    className: "map-pin-photo",
    html: `<div class="map-pin-photo-inner"><img src="${imageSrc}" alt="" /></div>`,
    iconSize: [PHOTO_PIN, PHOTO_PIN],
    iconAnchor: [PHOTO_PIN / 2, PHOTO_PIN],
    popupAnchor: [0, -PHOTO_PIN],
  });
}

const userGpsIcon = L.divIcon({
  className: "map-pin-user",
  html: '<div class="map-pin-user-dot" aria-hidden="true"></div>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  popupAnchor: [0, -11],
});

function iconForPlaceName(placeName) {
  if (placeName === MY_LOCATION) return userGpsIcon;
  if (placeName === "Library") return photoMarkerIcon(LIBRARY_IMG);
  if (placeName === "Main Building") return photoMarkerIcon(MAIN_BUILDING_IMG);
  if (placeName === "Food Court") return photoMarkerIcon(FOOD_COURT_IMG);
  if (placeName === "IT Department") return photoMarkerIcon(IT_DEPARTMENT_IMG);
  return defaultPinIcon;
}

function popupImageForPlace(placeName) {
  if (placeName === "Library") return LIBRARY_IMG;
  if (placeName === "Main Building") return MAIN_BUILDING_IMG;
  if (placeName === "Food Court") return FOOD_COURT_IMG;
  if (placeName === "IT Department") return IT_DEPARTMENT_IMG;
  return null;
}

function MarkerPopup({ placeName, gpsAccuracyM }) {
  if (placeName === MY_LOCATION) {
    return (
      <Popup className="map-place-popup">
        <div className="map-popup-body">
          <div className="map-popup-title">{MY_LOCATION}</div>
          <p className="map-popup-text">
            {gpsAccuracyM != null && Number.isFinite(gpsAccuracyM)
              ? `Approximate accuracy: ±${Math.round(gpsAccuracyM)} m. Route updates as you move (GPS). Stay outdoors for better signal.`
              : "Your live GPS position. The blue route updates while you walk. Allow location access if prompted."}
          </p>
        </div>
      </Popup>
    );
  }

  const imgSrc = popupImageForPlace(placeName);
  return (
    <Popup className="map-place-popup">
      <div className="map-popup-body">
        <div className="map-popup-title">{placeName}</div>
        {imgSrc ? (
          <img className="map-popup-img" src={imgSrc} alt={placeName} />
        ) : (
          <p className="map-popup-text">Tap the map to explore this location.</p>
        )}
      </div>
    </Popup>
  );
}

/** Fits map when `fitKey` changes (user tapped Navigate), not on every live GPS update */
function FitRouteToMap({ positions, fitKey }) {
  const map = useMap();
  const posRef = useRef(positions);
  posRef.current = positions;
  useEffect(() => {
    if (!fitKey) return;
    const p = posRef.current;
    if (!p?.length) return;
    if (p.length === 1) {
      map.setView(p[0], 18);
      return;
    }
    map.fitBounds(L.latLngBounds(p), { padding: [48, 48], maxZoom: 19 });
  }, [fitKey, map]);
  return null;
}

export default function ExploreTceMap() {
  const [from, setFrom] = useState(places[0].name);
  const [to, setTo] = useState(places[1].name);
  const [startFromGps, setStartFromGps] = useState(false);
  const [gpsError, setGpsError] = useState(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  /** Blue line + markers after Navigate; Library/Main Building use photo icons; click opens larger view */
  const [navResult, setNavResult] = useState(null);
  /** Increments only when user taps Navigate — map fitBounds uses this, not live updates */
  const [routeFitKey, setRouteFitKey] = useState(0);

  const toRef = useRef(to);
  toRef.current = to;
  const liveThrottleRef = useRef({ t: 0, lat: null, lng: null });

  useEffect(() => {
    setNavResult(null);
    setGpsError(null);
  }, [from, to, startFromGps]);

  useEffect(() => {
    if (!startFromGps || navResult?.fromName !== MY_LOCATION || !navigator.geolocation) {
      return undefined;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const now = Date.now();
        const th = liveThrottleRef.current;
        if (th.t > 0 && now - th.t < LIVE_REROUTE_MIN_MS) return;
        if (th.lat != null && th.lng != null) {
          const moved = haversineMeters({ lat, lng }, { lat: th.lat, lng: th.lng });
          if (moved < LIVE_REROUTE_MIN_M) return;
        }
        th.t = now;
        th.lat = lat;
        th.lng = lng;

        const toPlace = places.find((x) => x.name === toRef.current);
        if (!toPlace) return;

        const result = buildRouteFromPoints({ lat, lng }, toPlace, MY_LOCATION);
        setNavResult({ ...result, gpsAccuracyM: pos.coords.accuracy });
      },
      () => {
        /* keep last route; optional: setGpsError */
      },
      { enableHighAccuracy: true, maximumAge: 4000, timeout: 20000 }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  }, [startFromGps, navResult?.fromName]);

  const startIcon = useMemo(
    () => (navResult ? iconForPlaceName(navResult.fromName) : defaultPinIcon),
    [navResult?.fromName]
  );
  const endIcon = useMemo(
    () => (navResult ? iconForPlaceName(navResult.toName) : defaultPinIcon),
    [navResult?.toName]
  );

  function nav() {
    const toPlace = places.find((x) => x.name === to);
    if (!toPlace) return;

    if (startFromGps) {
      if (!navigator.geolocation) {
        setGpsError("Geolocation is not supported in this browser.");
        return;
      }
      setGpsLoading(true);
      setGpsError(null);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGpsLoading(false);
          liveThrottleRef.current = { t: 0, lat: null, lng: null };
          const fromPoint = {
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          };
          const result = buildRouteFromPoints(fromPoint, toPlace, MY_LOCATION);
          setRouteFitKey((k) => k + 1);
          setNavResult({ ...result, gpsAccuracyM: pos.coords.accuracy });
        },
        (err) => {
          setGpsLoading(false);
          setGpsError(
            err.code === 1
              ? "Location permission denied. Enable it in the browser to navigate from GPS."
              : err.message || "Could not read your location."
          );
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
      );
      return;
    }

    const fromPlace = places.find((x) => x.name === from);
    if (!fromPlace) return;

    setRouteFitKey((k) => k + 1);
    setNavResult(buildRouteFromPoints(fromPlace, toPlace, from));
  }

  return (
    <div className="map-page">
      <div className="map-top">
        <div className="map-panel">
          <label className="map-gps-toggle">
            <input
              type="checkbox"
              checked={startFromGps}
              onChange={(e) => setStartFromGps(e.target.checked)}
            />
            <span>From my GPS</span>
          </label>
          {startFromGps && (
            <p className="map-gps-hint">
              After Navigate, the blue line updates as you move (about every 5s or 12m).
            </p>
          )}
          <label className="map-panel-label" htmlFor="map-from">
            From
          </label>
          <select
            id="map-from"
            className="map-select"
            value={from}
            disabled={startFromGps}
            onChange={(e) => setFrom(e.target.value)}
          >
            {places.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
          <span className="map-arrow" aria-hidden>
            →
          </span>
          <label className="map-panel-label" htmlFor="map-to">
            To
          </label>
          <select
            id="map-to"
            className="map-select"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          >
            {places.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="map-nav-btn"
            onClick={nav}
            disabled={gpsLoading}
          >
            {gpsLoading ? "Locating…" : "Navigate"}
          </button>
        </div>
        {gpsError && <div className="map-gps-error">{gpsError}</div>}
      </div>

      <MapContainer
        center={[9.8835, 78.0815]}
        zoom={18}
        className="map-leaflet"
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {navResult?.coords?.length > 0 && (
          <FitRouteToMap positions={navResult.coords} fitKey={routeFitKey} />
        )}
        {navResult && navResult.coords.length > 1 && (
          <Polyline
            positions={navResult.coords}
            color="#2563eb"
            weight={6}
            opacity={0.92}
          />
        )}
        {navResult && (
          <>
            <Marker position={navResult.start} icon={startIcon}>
              <MarkerPopup
                placeName={navResult.fromName}
                gpsAccuracyM={navResult.gpsAccuracyM}
              />
            </Marker>
            <Marker position={navResult.end} icon={endIcon}>
              <MarkerPopup placeName={navResult.toName} />
            </Marker>
          </>
        )}
      </MapContainer>

      <div className="map-compass" aria-hidden>
        🧭
      </div>
    </div>
  );
}
