import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { DistrictPoint, DistrictResult } from "./types";
import { useEffect } from "react";

interface Props {
  districts: DistrictPoint[];
  results: Map<string, DistrictResult>;
  selected: string;
  onSelect: (district: string) => void;
}

function scoreColor(result?: DistrictResult): string {
  if (!result || result.status !== "complete") return "#8b9694";
  const score = Math.max(0, ...result.hazards.map((item) => item.raw_model_score * 100));
  if (score >= 75) return "#b84035";
  if (score >= 50) return "#ce7827";
  if (score >= 25) return "#b29a32";
  return "#3f8772";
}

function FocusDistrict({ point }: { point?: DistrictPoint }) {
  const map = useMap();
  useEffect(() => {
    if (point) map.flyTo([point.latitude, point.longitude], Math.max(map.getZoom(), 8), { duration: 0.45 });
  }, [map, point]);
  return null;
}

export default function MapView({ districts, results, selected, onSelect }: Props) {
  const current = districts.find((item) => item.name === selected);
  return (
    <MapContainer center={[33.92, 75.0]} zoom={7} minZoom={6} maxZoom={11} scrollWheelZoom className="district-map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FocusDistrict point={current} />
      {districts.map((point) => {
        const result = results.get(point.name);
        const selectedPoint = point.name === selected;
        return (
          <CircleMarker
            key={point.name}
            center={[point.latitude, point.longitude]}
            radius={selectedPoint ? 9 : 7}
            pathOptions={{
              color: selectedPoint ? "#20292b" : "#ffffff",
              weight: selectedPoint ? 3 : 2,
              fillColor: scoreColor(result),
              fillOpacity: result?.status === "complete" ? 0.92 : 0.7,
            }}
            eventHandlers={{ click: () => onSelect(point.name) }}
          >
            <Tooltip direction="top" offset={[0, -7]}>{point.name}</Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
