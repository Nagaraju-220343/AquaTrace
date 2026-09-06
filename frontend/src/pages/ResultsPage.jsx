import React, { useState, useEffect, useRef } from 'react';
import { RefreshCcw, Download, ImageOff, CheckCircle, XCircle, AlertCircle, Activity, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import './ResultsPage.css';

const API_BASE   = 'http://127.0.0.1:8000/api/v1';
// Images are mounted at /uploads/ on port 8000 — NOT under /api/v1/
const IMG_BASE   = 'http://127.0.0.1:8000';

// final_confidence  → 0-100 scale  (display as-is)
// detector_confidence → 0-1 scale  (multiply by 100 to display)
const fmtFinal = (v) => v != null ? v.toFixed(1) + '%' : '—';
const fmtDet   = (v) => v != null ? (v * 100).toFixed(1) + '%' : '—';

export default function ResultsPage({ jobId, jobImageUrl }) {
  const [detections, setDetections]   = useState([]);
  const [loading, setLoading]         = useState(false);
  const [jobs, setJobs]               = useState([]);
  const [selectedJob, setSelectedJob] = useState(jobId || '');
  const [imageUrl, setImageUrl]       = useState(null);
  const [imgLoaded, setImgLoaded]     = useState(false);
  const [viewMode, setViewMode]       = useState('pipeline'); // 'raw' or 'pipeline'
  const [zoom, setZoom]               = useState(1);
  const canvasRef = useRef();
  const imgRef    = useRef();

  // ── Fetch job list on mount ──────────────────────────────────────────────
  useEffect(() => { fetchJobs(); }, []);

  // ── Sync jobId prop → selectedJob when parent navigates here ────────────
  useEffect(() => {
    if (jobId) setSelectedJob(jobId);
  }, [jobId]);

  // ── When parent passes the image URL directly (freshest path), use it ───
  useEffect(() => {
    if (jobImageUrl) {
      setImageUrl(IMG_BASE + jobImageUrl);
      setImgLoaded(false);
    }
  }, [jobImageUrl]);

  // ── When selectedJob changes: fetch detections + set image URL ───────
  useEffect(() => {
    if (!selectedJob) {
      setDetections([]);
      setImageUrl(null);
      return;
    }
    fetchDetections(selectedJob);
    // Directly use the API endpoint to serve the image, avoiding 404 static mount issues
    setImageUrl(`${API_BASE}/analysis/image/${selectedJob}`);
    setImgLoaded(false);
    setZoom(1); // Reset zoom when switching jobs
  }, [selectedJob]);

  // ────────────────────────────────────────────────────────────────────────
  const fetchJobs = async () => {
    try {
      const res  = await fetch(`${API_BASE}/analysis/jobs`);
      const data = await res.json();
      setJobs(data);
    } catch (e) { console.error('Failed to fetch jobs:', e); }
  };

  const fetchDetections = async (jid) => {
    setLoading(true);
    try {
      const res  = await fetch(`${API_BASE}/analysis/detections/${jid}`);
      const data = await res.json();
      setDetections(data);
    } catch (e) { console.error('Failed to fetch detections:', e); }
    finally    { setLoading(false); }
  };

  // ── Draw bounding boxes on canvas after image loads ──────────────────────
  const drawBboxes = () => {
    const canvas = canvasRef.current;
    const img    = imgRef.current;
    if (!canvas || !img) return;

    canvas.width  = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!detections || !detections.length) return;

    detections.forEach(d => {
      // Filter based on view mode
      const isRejected = ['REJECT', 'REJECTED'].includes(d.decision?.toUpperCase());
      if (viewMode === 'pipeline' && isRejected) return;

      try {
        const bbox  = typeof d.bbox === 'string' ? JSON.parse(d.bbox) : d.bbox;
        const [x1, y1, x2, y2] = bbox;
        
        // In raw mode, use detector confidence. In pipeline mode, use final confidence.
        const conf  = viewMode === 'raw' 
                        ? (d.detector_confidence * 100)
                        : (d.final_confidence ?? (d.detector_confidence * 100));
                        
        // Color: Raw mode uses blue for everything. Pipeline uses confidence colors, or Red if rejected (though rejected are hidden in pipeline mode).
        let color = '#0e5a7a'; // default blue (Info)
        if (viewMode === 'pipeline') {
           color = conf >= 70 ? '#2f8f5c' : conf >= 40 ? '#b8791a' : '#0e5a7a';
        } else if (isRejected) {
           color = '#d93846'; // Highlight rejected ones in raw mode
        }

        // Box
        ctx.strokeStyle = color;
        ctx.lineWidth   = 4;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Label
        ctx.font = 'bold 28px Inter, sans-serif';
        const label = viewMode === 'raw' && isRejected ? `${d.class_name} (REJECTED)` : `${d.class_name}  ${conf.toFixed(0)}%`;
        const tw    = ctx.measureText(label).width;
        ctx.fillStyle = color;
        ctx.fillRect(x1, y1 - 36, tw + 14, 36);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, x1 + 7, y1 - 7);
      } catch (e) { console.warn('Bad bbox', d.bbox); }
    });
  };

  // Redraw whenever detections change, image finishes loading, or viewMode changes
  useEffect(() => {
    if (imgLoaded) drawBboxes();
  }, [detections, imgLoaded, viewMode]);

  // ── Stats ────────────────────────────────────────────────────────────────
  const avgConf = detections.length > 0
    ? (detections.reduce((s, d) => s + (d.final_confidence ?? 0), 0) / detections.length).toFixed(1) + '%'
    : '—';

  const decisionIcon = (decision) => {
    if (!decision) return null;
    const d = decision.toUpperCase();
    if (['ACCEPT', 'CONFIRMED'].includes(d)) return <CheckCircle size={14} style={{ color: 'var(--accent-lime)' }} />;
    if (['REJECT', 'REJECTED'].includes(d))  return <XCircle    size={14} style={{ color: 'var(--accent-rose)' }} />;
    return <AlertCircle size={14} style={{ color: 'var(--accent-amber)' }} />;
  };

  // ── Transparency: Extract Pipeline Info ──────────────────────────────────
  const pipelineInfo = {
    motionScore: detections.length > 0 && detections[0].evidence?.motion_quality_score != null
      ? (detections[0].evidence.motion_quality_score * 100).toFixed(0) + '%'
      : 'N/A',
    artifacts: detections.length > 0 && detections[0].evidence?.motion_quality_score != null && detections[0].evidence.motion_quality_score < 0.9
      ? 'Heave/Roll Detected'
      : 'None',
  };

  // ────────────────────────────────────────────────────────────────────────
  return (
    <div className="results-layout">

      {/* ── Left: job selector + detection table ────────────────────────── */}
      <div className="results-left">
        <div className="results-header">
          <div className="section-label">Analysis Results</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <select
              className="form-select job-select"
              value={selectedJob}
              onChange={e => setSelectedJob(e.target.value)}
            >
              <option value="">— Select a Job —</option>
              {jobs.map(j => (
                <option key={j.job_id} value={j.job_id}>
                  {j.job_id} ({j.status})
                </option>
              ))}
            </select>
            <button className="icon-btn" onClick={fetchJobs} title="Refresh jobs">
              <RefreshCcw size={15} />
            </button>
          </div>
        </div>

        {/* Stats row */}
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value">{detections.length}</div>
            <div className="stat-label">Detections</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--accent-lime)' }}>
              {detections.filter(d => ['ACCEPT','CONFIRMED'].includes(d.decision?.toUpperCase())).length}
            </div>
            <div className="stat-label">Confirmed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--accent-amber)' }}>
              {detections.filter(d => d.decision?.toUpperCase() === 'REVIEW').length}
            </div>
            <div className="stat-label">Review</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--accent-cyan)' }}>{avgConf}</div>
            <div className="stat-label">Avg Conf.</div>
          </div>
        </div>

        {/* Pipeline Transparency Card */}
        {selectedJob && detections.length > 0 && (
          <div className="table-wrap" style={{ padding: '16px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '20px' }}>
            <Activity size={24} style={{ color: 'var(--accent-cyan)' }} />
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Pipeline Quality (Transparency)</div>
              <div style={{ marginTop: '4px', fontSize: '14px', display: 'flex', gap: '16px' }}>
                <span><strong>Motion Score:</strong> <span style={{ color: pipelineInfo.motionScore !== 'N/A' && parseFloat(pipelineInfo.motionScore) < 80 ? 'var(--accent-amber)' : 'var(--accent-lime)' }}>{pipelineInfo.motionScore}</span></span>
                <span><strong>Artifacts:</strong> {pipelineInfo.artifacts}</span>
                <span><strong>Speckle Filter:</strong> Lee Adaptive</span>
              </div>
            </div>
          </div>
        )}

        {/* Detection table */}
        {selectedJob && (
          <div className="table-wrap">
            {loading ? (
              <div className="table-empty">Loading...</div>
            ) : detections.length === 0 ? (
              <div className="table-empty">
                <ImageOff size={32} style={{ color: 'var(--text-disabled)' }} />
                <p>No detections for this job.</p>
              </div>
            ) : (
              <table className="det-table">
                <thead>
                  <tr>
                    <th>Object</th><th>Class</th><th>Det. Conf.</th>
                    <th>Final Conf.</th><th>Decision</th><th>Lat</th><th>Lon</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.filter(d => {
                    const isRejected = ['REJECT', 'REJECTED'].includes(d.decision?.toUpperCase());
                    return viewMode === 'raw' ? true : !isRejected;
                  }).map(d => (
                    <tr key={d.object_id} style={{ opacity: ['REJECT', 'REJECTED'].includes(d.decision?.toUpperCase()) ? 0.5 : 1 }}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                        {d.object_id?.slice(-8) || '—'}
                      </td>
                      <td><span className="badge">{d.class_name || '—'}</span></td>
                      <td>{fmtDet(d.detector_confidence)}</td>
                      <td>{fmtFinal(d.final_confidence)}</td>
                      <td>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          {decisionIcon(d.decision)} {d.decision || '—'}
                        </span>
                      </td>
                      <td>{d.latitude?.toFixed(5) || '—'}</td>
                      <td>{d.longitude?.toFixed(5) || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Download report */}
        {selectedJob && (
          <div className="report-downloads">
            <div className="section-label">Download Report</div>
            <div style={{ display: 'flex', gap: 8 }}>
              {['json', 'csv'].map(fmt => (
                <a
                  key={fmt}
                  href={`${API_BASE}/analysis/report/${selectedJob}/${fmt}`}
                  className="btn btn-sm"
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  <Download size={13} /> .{fmt.toUpperCase()}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Right: Annotated image with bbox overlay ─────────────────────── */}
      <div className="results-right">
        <div className="section-label">Annotated Image</div>
        {/* View Mode & Zoom Controls */}
        {selectedJob && detections.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'space-between', marginBottom: '16px', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Image View Mode:</span>
              <button 
                className={`btn btn-sm ${viewMode === 'raw' ? 'active' : ''}`} 
                onClick={() => setViewMode('raw')}
                style={{ backgroundColor: viewMode === 'raw' ? 'var(--accent-cyan)' : 'transparent', border: '1px solid var(--border-active)' }}
              >
                Raw Model Predictions
              </button>
              <button 
                className={`btn btn-sm ${viewMode === 'pipeline' ? 'active' : ''}`} 
                onClick={() => setViewMode('pipeline')}
                style={{ backgroundColor: viewMode === 'pipeline' ? 'var(--color-success)' : 'transparent', color: viewMode === 'pipeline' ? '#fff' : 'var(--text-primary)', border: '1px solid var(--border-active)' }}
              >
                Pipeline Output
              </button>
            </div>
            
            {/* Zoom Controls */}
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
               <button className="icon-btn" onClick={() => setZoom(z => Math.max(1, z - 0.5))} title="Zoom Out">
                 <ZoomOut size={16} />
               </button>
               <span style={{ fontSize: '13px', minWidth: '40px', textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
               <button className="icon-btn" onClick={() => setZoom(z => Math.min(5, z + 0.5))} title="Zoom In">
                 <ZoomIn size={16} />
               </button>
               <button className="icon-btn" onClick={() => setZoom(1)} title="Reset Zoom">
                 <Maximize size={16} />
               </button>
            </div>
          </div>
        )}
        
        <div className="canvas-wrap">
          {imageUrl ? (
            <div className="zoom-container" style={{ width: `${zoom * 100}%`, height: `${zoom * 100}%` }}>
              <img
                ref={imgRef}
                src={imageUrl}
                alt="Sonar scan"
                className="result-img"
                onLoad={() => { setImgLoaded(true); drawBboxes(); }}
                onError={() => {
                  console.error('Image failed to load:', imageUrl);
                  setImageUrl(null);
                }}
              />
              <canvas ref={canvasRef} className="bbox-canvas" />
            </div>
          ) : (
            <div className="canvas-empty">
              <ImageOff size={48} style={{ color: 'var(--text-disabled)' }} />
              <p>
                {selectedJob
                  ? 'Image unavailable for this job.'
                  : 'Select a completed job to view annotated output'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
