import React, { useState, useRef, useCallback } from 'react';
import { UploadCloud, PlayCircle, Settings2, X, CheckCircle, Loader2, AlertTriangle } from 'lucide-react';
import './AnalyzePage.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1';

export default function AnalyzePage({ setJobId, setJobImageUrl, setActiveTab }) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [confidence, setConfidence] = useState(0.25);
  const [iou, setIou] = useState(0.45);
  const [sensor, setSensor] = useState('Klein 3000');
  const [altitude, setAltitude] = useState('');
  const [speed, setSpeed] = useState('');
  const [gpsLat, setGpsLat] = useState('');
  const [gpsLon, setGpsLon] = useState('');
  const [status, setStatus] = useState('idle'); // idle | uploading | running | done | error
  const [statusMsg, setStatusMsg] = useState('');
  const fileInputRef = useRef();

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreview(url);
    setStatus('idle');
    setStatusMsg('');
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const onDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = () => setDragOver(false);

  const handleRunAnalysis = async () => {
    if (!file) return;
    setStatus('uploading');
    setStatusMsg('Uploading image...');

    try {
      // Step 1: Upload file
      const formData = new FormData();
      formData.append('image', file);  // backend expects 'image'
      const uploadRes = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
      if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.statusText}`);
      const uploadData = await uploadRes.json();
      // The upload endpoint returns AnalysisJobRead which has input_file_path
      const filePath = uploadData.input_file_path;

      setStatus('running');
      setStatusMsg('Running detection pipeline...');

      // Step 2: Trigger analysis
      const metadata = {
        sensor_type: sensor,
        altitude_m: parseFloat(altitude) || null,
        speed_knots: parseFloat(speed) || null,
        gps_start_lat: parseFloat(gpsLat) || null,
        gps_start_lon: parseFloat(gpsLon) || null,
      };
      const runRes = await fetch(
        `${API_BASE}/analysis/run?file_path=${encodeURIComponent(filePath)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(metadata),
        }
      );
      if (!runRes.ok) throw new Error(`Analysis failed: ${runRes.statusText}`);
      const runData = await runRes.json();
      const { job_id } = runData;
      // Pass the image URL immediately so ResultsPage can show it without waiting
      if (runData.image_url && setJobImageUrl) setJobImageUrl(runData.image_url);
      setJobId(job_id);

      // Step 3: Poll for completion
      await pollJobStatus(job_id);
    } catch (err) {
      setStatus('error');
      setStatusMsg(err.message);
    }
  };

  const pollJobStatus = (job_id) => {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/analysis/status/${job_id}`);
          const data = await res.json();
          if (data.status === 'COMPLETED') {
            clearInterval(interval);
            setStatus('done');
            setStatusMsg(data.message || 'Analysis complete!');
            resolve();
            // Auto-navigate to results tab after 1.5s
            setTimeout(() => setActiveTab('results'), 1500);
          } else if (data.status === 'FAILED') {
            clearInterval(interval);
            setStatus('error');
            setStatusMsg(data.message || 'Pipeline failed.');
            reject(new Error(data.message));
          } else {
            setStatusMsg(`Status: ${data.status}...`);
          }
        } catch (e) {
          clearInterval(interval);
          reject(e);
        }
      }, 2000);
    });
  };

  const statusColors = { uploading: '--accent-amber', running: '--accent-cyan', done: '--accent-lime', error: '--accent-rose' };
  const StatusIcon = () => {
    if (status === 'uploading' || status === 'running') return <Loader2 size={16} className="spin" />;
    if (status === 'done') return <CheckCircle size={16} />;
    if (status === 'error') return <AlertTriangle size={16} />;
    return null;
  };

  return (
    <div className="analyze-layout">
      {/* LEFT PANEL */}
      <div className="analyze-left">
        {/* Drop Zone */}
        <div>
          <div className="section-label">Sonar Image Input</div>
          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/tiff"
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            {!file ? (
              <>
                <UploadCloud size={40} className="drop-icon" />
                <div className="drop-title">Drop sonar image here</div>
                <div className="drop-sub">PNG, JPG or TIFF — Side-scan sonar waterfall</div>
              </>
            ) : (
              <div className="drop-file-info">
                <CheckCircle size={20} className="file-ok-icon" />
                <span className="file-name">{file.name}</span>
                <button className="remove-btn" onClick={(e) => { e.stopPropagation(); setFile(null); setPreview(null); setStatus('idle'); }}>
                  <X size={14} />
                </button>
              </div>
            )}
          </div>
          {preview && <img src={preview} alt="preview" className="drop-preview" />}
        </div>

        {/* Sensor Config */}
        <div>
          <div className="section-label"><Settings2 size={12} style={{display:'inline', marginRight:5}} />Survey Metadata</div>
          <div className="form-group">
            <label className="form-label">Sensor Type</label>
            <select className="form-select" value={sensor} onChange={e => setSensor(e.target.value)}>
              <option>Klein 3000</option>
              <option>C-MAX CM2</option>
              <option>EdgeTech 4200</option>
              <option>Tritech StarFish</option>
              <option>Generic 100kHz</option>
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Altitude (m)</label>
              <input type="number" className="form-input" placeholder="e.g. 5" value={altitude} onChange={e => setAltitude(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Speed (knots)</label>
              <input type="number" className="form-input" placeholder="e.g. 2.5" value={speed} onChange={e => setSpeed(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">GPS Lat (start)</label>
              <input type="number" className="form-input" placeholder="e.g. 48.123" value={gpsLat} onChange={e => setGpsLat(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">GPS Lon (start)</label>
              <input type="number" className="form-input" placeholder="e.g. -122.456" value={gpsLon} onChange={e => setGpsLon(e.target.value)} />
            </div>
          </div>
        </div>

        {/* Detection Params */}
        <div>
          <div className="section-label">Detection Parameters</div>
          <div className="form-group">
            <label className="form-label">Confidence Threshold: <strong>{confidence.toFixed(2)}</strong></label>
            <input type="range" min={0.01} max={1} step={0.01} value={confidence} onChange={e => setConfidence(parseFloat(e.target.value))} className="slider" />
          </div>
          <div className="form-group">
            <label className="form-label">IoU Threshold: <strong>{iou.toFixed(2)}</strong></label>
            <input type="range" min={0.01} max={1} step={0.01} value={iou} onChange={e => setIou(parseFloat(e.target.value))} className="slider" />
          </div>
        </div>

        {/* Run Button */}
        <button
          className="btn run-btn"
          onClick={handleRunAnalysis}
          disabled={!file || status === 'uploading' || status === 'running'}
        >
          {status === 'uploading' || status === 'running'
            ? <Loader2 size={16} className="spin" />
            : <PlayCircle size={16} />}
          {status === 'uploading' ? 'Uploading...' : status === 'running' ? 'Running Pipeline...' : 'Run Analysis'}
        </button>

        {/* Status bar */}
        {status !== 'idle' && (
          <div className="status-bar" style={{ borderColor: `var(${statusColors[status] || '--border-active'})` }}>
            <span style={{ color: `var(${statusColors[status] || '--text-secondary'})`, display:'flex', alignItems:'center', gap:6 }}>
              <StatusIcon /> {statusMsg}
            </span>
          </div>
        )}
      </div>

      {/* RIGHT PANEL — Live Preview */}
      <div className="analyze-right">
        <div className="section-label">Sonar Preview</div>
        <div className="preview-panel">
          {preview ? (
            <img src={preview} alt="Sonar scan preview" className="preview-img" />
          ) : (
            <div className="preview-empty">
              <UploadCloud size={48} style={{ color: 'var(--text-disabled)' }} />
              <p>Upload a sonar image to preview it here</p>
            </div>
          )}
        </div>
        <div className="pipeline-steps">
          <div className="section-label" style={{ marginTop: 16 }}>Pipeline Steps</div>
          {['Ingestion', 'Pre-processing', 'YOLO Detection', 'Validation', 'Confidence Scoring', 'Geo-tagging', 'Reporting'].map((step, i) => (
            <div key={step} className="pipeline-step">
              <div className={`step-num ${status === 'running' ? 'active' : status === 'done' ? 'done' : ''}`}>{i + 1}</div>
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
