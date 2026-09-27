import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, ArrowUpRight, Check, Clock3, CloudSun, Database, LoaderCircle, MapPin, Radio, RefreshCw, ShieldAlert, Siren, Truck } from "lucide-react";
import { getAlerts, getDistricts, getExposure, getHealth, getResources, runPredictions, simulateAllocation } from "./api";
import MapView from "./MapView";
import type { AllocationRun, DevelopmentAlert, DistrictPoint, DistrictResult, Mode, PredictionRun, SimulatedExposure, SimulatedResource } from "./types";

const HAZARD_LABELS: Record<string, string> = {
  flood: "Flood",
  heavy_rain: "Heavy rain",
  landslide: "Landslide",
  heatwave: "Heatwave",
  coldwave: "Coldwave",
  windstorm: "Windstorm",
};

function developmentBand(score?: number | null): string {
  if (score == null) return "Unavailable";
  if (score >= 0.75) return "High development band";
  if (score >= 0.5) return "Elevated development band";
  if (score >= 0.25) return "Watch development band";
  return "Normal development band";
}

export default function App() {
  const [districts, setDistricts] = useState<DistrictPoint[]>([]);
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [alerts, setAlerts] = useState<DevelopmentAlert[]>([]);
  const [run, setRun] = useState<PredictionRun | null>(null);
  const [allocation, setAllocation] = useState<AllocationRun | null>(null);
  const [exposureRows, setExposureRows] = useState<SimulatedExposure[]>([]);
  const [resourceRows, setResourceRows] = useState<SimulatedResource[]>([]);
  const [mode, setMode] = useState<Mode>("historical_replay");
  const [selectedDistrict, setSelectedDistrict] = useState("Srinagar");
  const [activeTab, setActiveTab] = useState<"scores" | "resources" | "alerts">("scores");
  const [busy, setBusy] = useState(false);
  const [allocating, setAllocating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getDistricts(), getHealth(), getAlerts(), getExposure(), getResources()])
      .then(([districtPayload, status, alertPayload, exposurePayload, resourcePayload]) => {
        setDistricts(districtPayload.districts);
        setHealth(status);
        setAlerts(alertPayload.alerts);
        setExposureRows(exposurePayload.districts);
        setResourceRows(resourcePayload.resources);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const results = useMemo(() => new Map((run?.district_results || []).map((item) => [item.district, item])), [run]);
  const selectedResult = results.get(selectedDistrict);
  const readyCount = run?.district_count ?? 0;

  async function refreshStatus() {
    try { setHealth(await getHealth()); } catch { /* the main action reports request errors */ }
  }

  async function onRun() {
    setBusy(true);
    setError("");
    setAllocation(null);
    try {
      const next = await runPredictions(mode);
      setRun(next);
      const alertPayload = await getAlerts();
      setAlerts(alertPayload.alerts);
      setActiveTab("scores");
      await refreshStatus();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not run the assessment");
    } finally {
      setBusy(false);
    }
  }

  async function onAllocate() {
    if (!run) return;
    setAllocating(true);
    setError("");
    try {
      setAllocation(await simulateAllocation(run.id));
      setActiveTab("resources");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not prepare the simulation");
    } finally {
      setAllocating(false);
    }
  }

  const selectedPoint = districts.find((item) => item.name === selectedDistrict);
  const scoreOrder = selectedResult?.hazards || [];
  const selectedAllocation = allocation?.allocations.find((item) => item.district === selectedDistrict);
  const selectedExposure = exposureRows.find((item) => item.district === selectedDistrict);
  const selectedResources = resourceRows.filter((item) => item.district === selectedDistrict);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-icon"><Activity size={19} strokeWidth={2.2} /></div>
          <div><div className="brand-title">JK Hazard Console</div><div className="brand-subtitle">DISTRICT DEVELOPMENT SYSTEM</div></div>
        </div>
        <div className="service-state">
          <span className={`state-dot ${health.status === "ready" ? "is-ready" : ""}`} />
          <span>{health.status === "ready" ? "API ready" : "API unavailable"}</span>
          <span className="state-divider" />
          <Database size={14} />
          <span>{String(health.supabase || "Local store")}</span>
          <button className="icon-button state-refresh" title="Refresh service status" aria-label="Refresh service status" onClick={refreshStatus}><RefreshCw size={14} /></button>
        </div>
      </header>

      <main>
        <section className="page-toolbar">
          <div className="page-heading">
            <span className="eyebrow">JAMMU & KASHMIR · 20 DISTRICTS</span>
            <h1>Hazard outlook</h1>
          </div>
          <div className="toolbar-actions">
            <div className="mode-switch" role="group" aria-label="Weather input mode">
              <button className={mode === "historical_replay" ? "active" : ""} onClick={() => setMode("historical_replay")} title="Use the fixed historical weather replay"><Clock3 size={15} /> Replay</button>
              <button className={mode === "live" ? "active" : ""} onClick={() => setMode("live")} title="Fetch current ECMWF weather inputs"><CloudSun size={15} /> Live</button>
              <button className={mode === "simulated_demo" ? "active" : ""} onClick={() => setMode("simulated_demo")} title="Use the explicitly synthetic offline weather fixture"><Database size={15} /> Demo</button>
            </div>
            <button className="primary-button" onClick={onRun} disabled={busy || districts.length === 0}>
              {busy ? <LoaderCircle size={16} className="spin" /> : <Radio size={16} />}
              {busy ? "Running" : "Run assessment"}
            </button>
          </div>
        </section>

        <div className="scope-banner">
          <ShieldAlert size={17} />
          <strong>DEVELOPMENT / SIMULATION ONLY</strong>
          <span>Not for public warning · not for real dispatch · synthetic labels and resources</span>
        </div>

        {error && <div className="error-banner" role="alert"><AlertTriangle size={16} />{error}</div>}

        <section className="workspace-grid">
          <section className="map-panel" aria-label="District weather reference map">
            <div className="map-heading">
              <div><MapPin size={16} /><span>District weather references</span></div>
              <span className="map-meta">{run ? `${readyCount}/20 evaluated` : "20 reference points"}</span>
            </div>
            <div className="map-wrap">
              <MapView districts={districts} results={results} selected={selectedDistrict} onSelect={setSelectedDistrict} />
              <div className="map-legend">
                <span className="legend-title">MAX RAW SCORE · DISPLAY SCALE</span>
                <span><i className="legend-dot score-low" />0–24</span>
                <span><i className="legend-dot score-mid" />25–49</span>
                <span><i className="legend-dot score-high" />50–74</span>
                <span><i className="legend-dot score-extreme" />75+</span>
              </div>
            </div>
            <div className="map-footnote">Markers show source weather lookup coordinates, not district boundaries or centroids.</div>
          </section>

          <aside className="inspector">
            <div className="inspector-heading">
              <div><span className="eyebrow">DISTRICT DETAIL</span><h2>{selectedDistrict}</h2></div>
              <select value={selectedDistrict} onChange={(event) => setSelectedDistrict(event.target.value)} aria-label="Select district">
                {districts.map((district) => <option key={district.name} value={district.name}>{district.name}</option>)}
              </select>
            </div>

            {run ? <div className="date-line"><span>{run.mode === "live" ? <CloudSun size={14} /> : run.mode === "simulated_demo" ? <Database size={14} /> : <Clock3 size={14} />}{run.mode === "live" ? "Live weather" : run.mode === "simulated_demo" ? "SIMULATED_DEMO_WEATHER" : "Historical replay"}</span><span>{run.feature_reference_date} → {run.target_date}</span></div> : <div className="empty-state"><Siren size={21} /><span>No assessment run</span><small>Choose an input mode and run an assessment.</small></div>}

            <div className="inspector-tabs" role="tablist" aria-label="District views">
              <button className={activeTab === "scores" ? "active" : ""} onClick={() => setActiveTab("scores")} role="tab">Hazards</button>
              <button className={activeTab === "resources" ? "active" : ""} onClick={() => setActiveTab("resources")} role="tab">Resource Planning</button>
              <button className={activeTab === "alerts" ? "active" : ""} onClick={() => setActiveTab("alerts")} role="tab">Signals <span className="tab-count">{alerts.length}</span></button>
            </div>

            {activeTab === "scores" && <div className="tab-content">
              {selectedResult?.status === "complete" ? <>
                <div className="weather-strip">
                  <div><span>MEAN TEMP</span><strong>{selectedResult.weather_summary?.temperature_mean_c.toFixed(1)}</strong><small>°C</small></div>
                  <div><span>PRECIPITATION</span><strong>{selectedResult.weather_summary?.precipitation_total_mm.toFixed(1)}</strong><small>mm</small></div>
                  <div><span>WIND MEAN</span><strong>{selectedResult.weather_summary?.wind_speed_mean_kmh.toFixed(1)}</strong><small>km/h</small></div>
                </div>
                <div className="combined-risk-line">
                  <span>{developmentBand(selectedResult.combined_development_risk_score)} · max raw hazard score</span>
                  <strong>{selectedResult.combined_development_risk_score?.toFixed(4) ?? "Unavailable"}</strong>
                </div>
                <div className="score-heading"><h3>Development model scores</h3><span>uncalibrated</span></div>
                <div className="hazard-list">
                  {scoreOrder.map((item) => <div className="hazard-row" key={item.hazard}>
                    <div className="hazard-label"><span>{HAZARD_LABELS[item.hazard] || item.hazard}</span>{item.above_validation_threshold && <span className="signal-label"><AlertTriangle size={11} /> SIGNAL</span>}</div>
                    <div className="score-line"><div className="score-track"><div style={{ width: `${Math.min(100, item.raw_model_score * 100)}%` }} /></div><strong>{item.raw_model_score.toFixed(4)}</strong></div>
                    <div className="threshold-line">Validation raw-score threshold {item.validation_threshold_score.toFixed(4)}</div>
                  </div>)}
                </div>
                {selectedPoint && <div className="source-note"><span>WEATHER INPUT · {selectedResult.weather_scope || "scope unavailable"}</span><strong>{selectedResult.source}</strong><small>{selectedPoint.latitude.toFixed(2)}, {selectedPoint.longitude.toFixed(2)}</small><small>Data timestamp: {selectedResult.retrieved_at ? new Date(selectedResult.retrieved_at).toLocaleString() : run?.data_freshness?.data_as_of || run?.data_freshness?.status || "not available"}</small></div>}
              </> : selectedResult?.status === "unavailable" ? <div className="empty-state"><AlertTriangle size={20} /><span>Inputs unavailable</span><small>{selectedResult.reason}</small></div> : <div className="empty-state"><Activity size={20} /><span>Awaiting assessment</span><small>Scores appear here after a successful run.</small></div>}
            </div>}

            {activeTab === "resources" && <div className="tab-content resource-planning">
              <div className="simulation-stop"><ShieldAlert size={15} /><strong>SIMULATION ONLY · NOT FOR REAL DISPATCH</strong></div>
              {selectedExposure && <div className="exposure-grid">
                <div><span>SIMULATED POPULATION</span><strong>{selectedExposure.simulated_population.toLocaleString()}</strong></div>
                <div><span>EXPOSURE INDEX</span><strong>{selectedExposure.simulated_exposure_index.toFixed(2)}</strong></div>
                <div><span>VULNERABILITY</span><strong>{selectedExposure.simulated_vulnerability_index.toFixed(2)}</strong></div>
              </div>}
              <div className="resource-heading"><h3>Simulated availability</h3><span>{selectedResources.length} records · phase9_simulation_v1</span></div>
              <div className="resource-stock-list">{selectedResources.map((item) => <div key={item.resource_id}><span>{item.resource_type.replaceAll("_", " ")}</span><strong className={`stock-${item.status}`}>{item.available_capacity.toLocaleString()} / {item.total_capacity.toLocaleString()} {item.capacity_unit.replaceAll("_", " ")}</strong></div>)}</div>
              {!allocation ? <div className="empty-state compact"><Truck size={18} /><span>No response plan yet</span><small>Run an assessment and simulate a plan to see recommendations.</small>{run && <button className="secondary-button" onClick={onAllocate} disabled={allocating}>{allocating ? <LoaderCircle size={15} className="spin" /> : <Truck size={15} />}Simulate resource plan</button>}</div> : <>
                <div className="resource-heading"><h3>District recommendation</h3><span>{selectedAllocation ? `${selectedAllocation.priority_score.toFixed(1)} priority` : "No assignment"}</span></div>
                {selectedAllocation ? <>
                  <p className="allocation-formula">{selectedAllocation.allocation_reason}</p>
                  <div className="priority-breakdown">{Object.entries(selectedAllocation.priority_components).filter(([name]) => name !== "priority_score").map(([name, value]) => <div key={name}><span>{name.replaceAll("_component", "").replaceAll("_", " ")}</span><b>{value.toFixed(1)}</b></div>)}</div>
                  <div className="resource-assignment-list">{selectedAllocation.resource_assignments.map((item) => <div key={item.resource_id}><div><strong>{item.resource_type.replaceAll("_", " ")}</strong><small>{item.resource_district} · {item.estimated_travel_time_minutes.toFixed(0)} simulated min</small></div><b>{item.allocated_capacity.toLocaleString()} {item.capacity_unit.replaceAll("_", " ")}</b></div>)}</div>
                  {selectedAllocation.unmet_needs.length > 0 && <div className="unmet-list"><strong>Unmet in this simulation</strong>{selectedAllocation.unmet_needs.map((need) => <span key={need.resource_type}>{need.resource_type.replaceAll("_", " ")}: {need.reason}</span>)}</div>}
                </> : <div className="empty-state compact"><span>No simulated assignment for {selectedDistrict}</span><small>No signal or no compatible resource inside the travel limit.</small></div>}
                <div className="production-gap"><strong>Real operational inputs unavailable</strong><span>Official population, vulnerability, resource stock, suitability, road routing, and capacity data are not connected.</span></div>
                <div className="remaining-stock"><span>REMAINING SIMULATED CAPACITY</span>{Object.entries(allocation.inventory.remaining).map(([name, count]) => <div key={name}><span>{name.replaceAll("_", " ")}</span><b>{count.toLocaleString()}</b></div>)}</div>
              </>}
            </div>}

            {activeTab === "alerts" && <div className="tab-content">
              <div className="simulated-note alert-note"><AlertTriangle size={15} /><span>DEVELOPMENT SIGNALS · OUTBOUND NOTIFICATIONS DISABLED</span></div>
              {alerts.length === 0 ? <div className="empty-state compact"><span>No signals recorded</span><small>Threshold exceedances appear after a run.</small></div> : <div className="alert-list">{alerts.slice(0, 30).map((item) => { const rawScore = item.raw_model_score ?? (item.score > 1 ? item.score / 100 : item.score); const threshold = item.validation_threshold_score ?? (item.threshold > 1 ? item.threshold / 100 : item.threshold); return <div className="alert-row" key={item.id}><span className="alert-mark"><Siren size={14} /></span><div><strong>{item.district} · {HAZARD_LABELS[item.hazard] || item.hazard} · {item.alert_level || "WATCH"}</strong><small>raw {rawScore.toFixed(4)} · threshold {threshold.toFixed(4)} · {item.model_version || "phase7f_v1"}</small><small>{item.reason || "Development threshold exceedance"} · {item.data_source || "source unavailable"} · {new Date(item.created_at).toLocaleString()}</small></div><ArrowUpRight size={14} /></div>; })}</div>}
            </div>}

            {run && <div className="inspector-bottom">
              {activeTab !== "resources" && <button className="secondary-button allocation-cta" onClick={onAllocate} disabled={allocating}>{allocating ? <LoaderCircle size={15} className="spin" /> : <Truck size={15} />}Simulate resource plan</button>}
              <div className="provenance-line"><Check size={13} /><span>Phase 5 predictors · one-day alignment</span></div>
            </div>}
          </aside>
        </section>

        <section className="run-strip">
          <div className="run-strip-title"><span className="run-indicator" /><div><strong>{run ? `Run ${run.id.slice(0, 8)}` : "No run selected"}</strong><small>{run ? `${run.source} · ${run.created_at ? new Date(run.created_at).toLocaleString() : "just now"}` : "Assessment history will appear after the first run."}</small></div></div>
          <div className="run-strip-stats"><div><span>DISTRICTS</span><strong>{run ? `${readyCount}/20` : "—"}</strong></div><div><span>DATE WINDOW</span><strong>{run ? run.target_date : "—"}</strong></div><div><span>SCOPE</span><strong className="scope-value">SYNTHETIC DEV</strong></div></div>
        </section>
      </main>

      <footer className="app-footer"><span>Phase 7A rules · {String(health.model_version || "phase7f_v1")}</span><span>Persistence: {String(health.supabase || "checking")}</span><span>NOT FOR PUBLIC WARNING OR REAL DISPATCH</span><span>Notifications: disabled</span></footer>
    </div>
  );
}
