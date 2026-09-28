import React, { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { RefreshCcw, Map as MapIcon, Image as ImageIcon, Trash2 } from 'lucide-react';
import L from 'leaflet';
import './MapPage.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1';
const IMG_BASE = import.meta.env.VITE_IMG_BASE || 'http://127.0.0.1:8000';

// Fix for default Leaflet marker icons in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom icons based on decision
const createCustomIcon = (color) =>
  new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });

const icons = {
  ACCEPT:    createCustomIcon('green'),
  CONFIRMED: createCustomIcon('green'),
  REVIEW:    createCustomIcon('orange'),
  REJECT:    createCustomIcon('red'),
  REJECTED:  createCustomIcon('red'),
  DEFAULT:   createCustomIcon('blue'),
};

export default function MapPage() {
  const [latestJob, setLatestJob]     = useState(null);   // { job_id, status, ... }
  const [detections, setDetections]   = useState([]);
  const [loading, setLoading]         = useState(false);
  const [resetting, setResetting]     = useState(false);
  const [statusMsg, setStatusMsg]     = useState('');

  // On mount: fetch the latest completed job
  const fetchLatestJob = useCallback(async () => {
    setLoading(true);
    setStatusMsg('');
    try {
      const res  = await fetch(`${API_BASE}/analysis/jobs`);
      const jobs = await res.json();
      const completed = jobs.filter(j => j.status === 'COMPLETED');
      if (completed.length > 0) {
        const job = completed[0]; // already ordered desc by created_at
        setLatestJob(job);
        await fetchDetections(job.job_id);
      } else {
        setLatestJob(null);
        setDetections([]);
        setStatusMsg('No completed analysis jobs found. Run an analysis first.');
      }
    } catch (e) {
      setStatusMsg('Failed to fetch jobs. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDetections = async (jobId) => {
    try {
      const res  = await fetch(`${API_BASE}/analysis/detections/${jobId}`);
      const data = await res.json();
      setDetections(data);
    } catch (e) {
      console.error('Failed to fetch detections:', e);
    }
  };

  // Reset: delete ALL jobs + detections, clear UI
  const handleReset = async () => {
    if (!window.confirm('Delete ALL jobs and detections? This cannot be undone.')) return;
    setResetting(true);
    try {
      await fetch(`${API_BASE}/analysis/jobs/all`, { method: 'DELETE' });
      setLatestJob(null);
      setDetections([]);
      setStatusMsg('All jobs cleared. Run a new analysis to begin.');
    } catch (e) {
      setStatusMsg('Reset failed: ' + e.message);
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => {
    fetchLatestJob();
  }, [fetchLatestJob]);

  // Show all detections that have valid coordinates (REJECTs shown in red)
  const mappedDetections = detections.filter(
    d => d.latitude != null && d.longitude != null
  );

  const defaultCenter = [13.0, 80.0];
  const center =
    mappedDetections.length > 0
      ? [
          mappedDetections.reduce((s, d) => s + d.latitude,  0) / mappedDetections.length,
          mappedDetections.reduce((s, d) => s + d.longitude, 0) / mappedDetections.length,
        ]
      : defaultCenter;

  return (
    <div className="map-layout">
      <div className="map-header">
        <div className="map-title">
          <MapIcon size={20} className="title-icon" />
          <span>Geospatial Detection Map</span>
        </div>

        <div className="map-actions" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Current job badge */}
          {latestJob && (
            <span style={{
              fontSize: '12px',
              padding: '4px 10px',
              borderRadius: '4px',
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontFamily: 'monospace',
            }}>
              {latestJob.job_id}
            </span>
          )}

          {/* Refresh — re-fetches latest job */}
          <button
            className="icon-btn"
            onClick={fetchLatestJob}
            title="Refresh latest job"
            disabled={loading}
          >
            <RefreshCcw size={16} className={loading ? 'spin' : ''} />
          </button>

          {/* Reset — deletes everything */}
          <button
            className="icon-btn"
            onClick={handleReset}
            title="Delete all jobs and reset"
            disabled={resetting}
            style={{ color: 'var(--accent-rose, #f87171)' }}
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* Status message (no jobs / error) */}
      {statusMsg && (
        <div style={{
          padding: '10px 16px',
          fontSize: '13px',
          color: 'var(--text-secondary)',
          background: 'var(--bg-raised)',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          {statusMsg}
        </div>
      )}

      <div className="map-container-wrap">
        {loading ? (
          <div className="map-loading">Loading latest detection data…</div>
        ) : !latestJob ? (
          <div className="map-loading">No completed jobs yet. Run an analysis to see results here.</div>
        ) : (
          <MapContainer
            center={center}
            zoom={mappedDetections.length > 0 ? 12 : 5}
            scrollWheelZoom={true}
            className="leaflet-map"
            key={latestJob.job_id}
          >
            <TileLayer
              attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
            {mappedDetections.map((det) => {
              const icon = icons[det.decision?.toUpperCase()] || icons.DEFAULT;
              return (
                <Marker
                  key={det.object_id}
                  position={[det.latitude, det.longitude]}
                  icon={icon}
                >
                  <Popup className="dark-popup">
                    <div className="popup-content">
                      <div className="popup-header">
                        <span className="badge">{det.class_name}</span>
                        <span className={`decision-dot ${det.decision?.toLowerCase()}`}></span>
                      </div>
                      <div className="popup-body">
                        <p><strong>Decision:</strong> {det.decision || 'N/A'}</p>
                        <p><strong>Confidence:</strong> {det.final_confidence ? det.final_confidence.toFixed(1) + '%' : 'N/A'}</p>
                        <p><strong>Lat:</strong> {det.latitude.toFixed(5)}</p>
                        <p><strong>Lon:</strong> {det.longitude.toFixed(5)}</p>
                        {det.dimensions_meters && (
                          <p><strong>Size:</strong> {det.dimensions_meters[0]}m × {det.dimensions_meters[1]}m</p>
                        )}
                      </div>
                      <a
                        href={`${IMG_BASE}/uploads/${latestJob.image_url?.split('/uploads/')[1] || ''}`}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-sm btn-full mt-2"
                        style={{ justifyContent: 'center', backgroundColor: 'var(--bg-hover)' }}
                      >
                        <ImageIcon size={14} /> View Sonar Image
                      </a>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        )}
      </div>

      {/* Detection summary footer */}
      {latestJob && (
        <div style={{
          padding: '8px 16px',
          fontSize: '12px',
          color: 'var(--text-secondary)',
          display: 'flex',
          gap: 16,
          borderTop: '1px solid var(--border-subtle)',
        }}>
          <span>📍 <strong>{mappedDetections.length}</strong> plotted detection{mappedDetections.length !== 1 ? 's' : ''}</span>
          <span>🔎 <strong>{detections.length - mappedDetections.length}</strong> without GPS (geotagging unavailable)</span>
        </div>
      )}
    </div>
  );
}
