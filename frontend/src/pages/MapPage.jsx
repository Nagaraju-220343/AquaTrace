import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { RefreshCcw, Map as MapIcon, Image as ImageIcon } from 'lucide-react';
import L from 'leaflet';
import './MapPage.css';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

// Fix for default Leaflet marker icons in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom icons based on decision
const createCustomIcon = (color) => {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
};

const icons = {
  ACCEPT: createCustomIcon('green'),
  CONFIRMED: createCustomIcon('green'),
  REVIEW: createCustomIcon('orange'),
  REJECT: createCustomIcon('red'),
  DEFAULT: createCustomIcon('blue')
};

export default function MapPage() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState('');
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/analysis/jobs`);
      const data = await res.json();
      setJobs(data);
      const completed = data.filter(j => j.status === 'COMPLETED');
      if (completed.length > 0 && !selectedJob) {
        setSelectedJob(completed[0].job_id);
      }
    } catch (e) {
      console.error('Failed to fetch jobs:', e);
    }
  };

  useEffect(() => {
    if (selectedJob) {
      fetchDetections(selectedJob);
    } else {
      setDetections([]);
    }
  }, [selectedJob]);

  const fetchDetections = async (jid) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/analysis/detections/${jid}`);
      const data = await res.json();
      setDetections(data);
    } catch (e) {
      console.error('Failed to fetch detections:', e);
    } finally {
      setLoading(false);
    }
  };

  // Filter out rejected detections for "pipeline output" view
  const pipelineDetections = detections.filter(d => 
    !['REJECT', 'REJECTED'].includes(d.decision?.toUpperCase()) && 
    d.latitude != null && 
    d.longitude != null
  );

  // Determine initial center. Default to roughly Indian Ocean / Bay of Bengal if no data
  const defaultCenter = [13.0, 80.0];
  const center = pipelineDetections.length > 0 
    ? [pipelineDetections[0].latitude, pipelineDetections[0].longitude] 
    : defaultCenter;

  return (
    <div className="map-layout">
      <div className="map-header">
        <div className="map-title">
          <MapIcon size={20} className="title-icon" />
          <span>Geospatial Detection Map</span>
        </div>
        <div className="map-actions">
          <select
            className="form-select"
            value={selectedJob}
            onChange={(e) => setSelectedJob(e.target.value)}
            style={{ fontSize: '12px', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border-subtle)', background: 'var(--bg-raised)', color: 'var(--text-primary)' }}
          >
            <option value="">— Select a Job —</option>
            {jobs.filter(j => j.status === 'COMPLETED').map(j => (
              <option key={j.job_id} value={j.job_id}>
                {j.job_id}
              </option>
            ))}
          </select>
          <span className="det-count" style={{ display: 'none' }}></span>
          <button className="icon-btn" onClick={() => fetchDetections(selectedJob)} title="Refresh Map" disabled={!selectedJob}>
            <RefreshCcw size={16} />
          </button>
        </div>
      </div>
      
      <div className="map-container-wrap">
        {loading ? (
          <div className="map-loading">Loading Geospatial Data...</div>
        ) : !selectedJob ? (
          <div className="map-loading">Select a completed job to view mappings.</div>
        ) : (
          <MapContainer center={center} zoom={18} scrollWheelZoom={true} className="leaflet-map" key={selectedJob}>
            <TileLayer
              attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
            {pipelineDetections.map((det) => {
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
                        <p><strong>Job:</strong> {det.job_id ? det.job_id.split('-')[1] : selectedJob.split('-')[1]}</p>
                        <p><strong>Confidence:</strong> {det.final_confidence ? (det.final_confidence).toFixed(1) + '%' : 'N/A'}</p>
                        <p><strong>Lat:</strong> {det.latitude.toFixed(5)}</p>
                        <p><strong>Lon:</strong> {det.longitude.toFixed(5)}</p>
                        {det.dimensions_meters && (
                          <p><strong>Size:</strong> {det.dimensions_meters[0]}m x {det.dimensions_meters[1]}m</p>
                        )}
                      </div>
                      <a href={`http://127.0.0.1:8000/api/v1/analysis/image/${selectedJob}`} target="_blank" rel="noreferrer" className="btn btn-sm btn-full mt-2" style={{justifyContent: 'center', backgroundColor: 'var(--bg-hover)'}}>
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
    </div>
  );
}
