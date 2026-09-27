import type { AllocationRun, DevelopmentAlert, DistrictPoint, Mode, PredictionRun, SimulatedExposure, SimulatedResource } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : body.detail?.message;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getHealth = () => request<Record<string, unknown>>("/api/health");
export const getDistricts = () => request<{ districts: DistrictPoint[] }>("/api/districts");
export const getAlerts = () => request<{ alerts: DevelopmentAlert[] }>("/api/alerts");
export const getResources = () => request<{ resources: SimulatedResource[]; simulation_version: string }>("/api/resources");
export const getExposure = () => request<{ districts: SimulatedExposure[]; simulation_version: string }>("/api/exposure");
export const runPredictions = (mode: Mode) =>
  request<PredictionRun>("/api/predictions", { method: "POST", body: JSON.stringify({ mode }) });
export const simulateAllocation = (runId: string) =>
  request<AllocationRun>("/api/allocations/simulate", { method: "POST", body: JSON.stringify({ run_id: runId }) });
