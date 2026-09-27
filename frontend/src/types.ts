export type Mode = "historical_replay" | "live" | "simulated_demo";

export interface DistrictPoint {
  name: string;
  latitude: number;
  longitude: number;
  coordinate_type: string;
}

export interface HazardScore {
  hazard: string;
  raw_model_score: number;
  raw_model_score_pct_for_display: number;
  development_score_pct: number;
  validation_threshold_score: number;
  validation_threshold_pct: number;
  above_validation_threshold: boolean;
  calibrated_probability: false;
  score_semantics: string;
  label_scope: string;
  model_version: string;
}

export interface DistrictResult {
  district: string;
  status: "complete" | "unavailable";
  feature_reference_date?: string;
  target_date?: string;
  source?: string;
  reason?: string;
  weather_scope?: string;
  retrieved_at?: string | null;
  fixture_version?: string | null;
  weather_summary?: {
    temperature_mean_c: number;
    precipitation_total_mm: number;
    wind_speed_mean_kmh: number;
    weather_code: number;
  };
  active_hazard_signals?: string[];
  combined_development_risk_score?: number | null;
  combined_risk_method?: string;
  model_version?: string;
  label_scope?: string;
  hazards: HazardScore[];
}

export interface PredictionRun {
  id: string;
  mode: Mode;
  source: string;
  feature_reference_date: string;
  target_date: string;
  created_at: string;
  data_freshness?: {
    status: string;
    retrieved_at: string | null;
    source: string;
    fixture_version?: string;
    data_as_of?: string;
  };
  status: string;
  district_count: number;
  unavailable_district_count: number;
  district_results: DistrictResult[];
  operational_use: string;
  model_version?: string;
  label_scope?: string;
  combined_risk_method?: string;
}

export interface AllocationRun {
  id: string;
  status: string;
  priority_formula: string;
  simulation_version: string;
  operational_disclaimer: string;
  input_availability: Record<string, string>;
  production_input_availability: Record<string, { status: string; source: string | null }>;
  inventory: {
    scope: string;
    source: string;
    items: Record<string, number>;
    remaining: Record<string, number>;
  };
  allocations: {
    district: string;
    priority_score: number;
    priority_components: Record<string, number>;
    raw_model_score: number;
    simulation_priority: number;
    development_signals: string[];
    allocation_reason: string;
    simulated_population: number;
    simulated_exposure_index: number;
    simulated_vulnerability_index: number;
    estimated_travel_time_minutes: number | null;
    resource_assignments: {
      resource_id: string;
      resource_type: string;
      resource_district: string;
      allocated_capacity: number;
      capacity_unit: string;
      estimated_travel_time_minutes: number;
      status: string;
    }[];
    unmet_needs: { resource_type: string; requested_capacity: number; reason: string }[];
    simulated_assignment: Record<string, number>;
  }[];
}

export interface SimulatedExposure {
  district: string;
  simulated_population: number;
  simulated_exposure_index: number;
  simulated_vulnerability_index: number;
  data_scope: "SIMULATED_DEVELOPMENT_ONLY";
  simulation_version: string;
}

export interface SimulatedResource {
  resource_id: string;
  resource_type: string;
  district: string;
  available_capacity: number;
  total_capacity: number;
  capacity_unit: string;
  status: string;
  suitable_hazards: string[];
  simulation_version: string;
  data_scope: "SIMULATED_DEVELOPMENT_ONLY";
}

export interface DevelopmentAlert {
  id: string;
  district: string;
  hazard: string;
  score: number;
  threshold: number;
  raw_model_score?: number;
  validation_threshold_score?: number;
  score_semantics?: string;
  status: string;
  created_at: string;
  alert_level?: "NORMAL" | "WATCH" | "ELEVATED" | "HIGH";
  reason?: string;
  data_source?: string;
  model_version?: string;
  development_status?: string;
}
