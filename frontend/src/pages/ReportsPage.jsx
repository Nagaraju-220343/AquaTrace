import React, { useState, useEffect, useRef } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './ReportsPage.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1';

export default function ReportsPage() {
  const [jobs, setJobs] = useState([]);
  const [allDetections, setAllDetections] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const jobsRes = await fetch(`${API_BASE}/analysis/jobs`);
      const jobsData = await jobsRes.json();
      setJobs(jobsData);

      const completedJobs = jobsData.filter(j => j.status === 'COMPLETED');
      const allDets = [];
      for (const job of completedJobs) {
        const detRes = await fetch(`${API_BASE}/analysis/detections/${job.job_id}`);
        const dets = await detRes.json();
        allDets.push(...dets.map(d => ({ ...d, job_id: job.job_id })));
      }
      setAllDetections(allDets);
    } catch (e) {
      console.error('Failed to load report data:', e);
    } finally {
      setLoading(false);
    }
  };

  // --- Chart Data ---
  const classCounts = allDetections.reduce((acc, d) => {
    const cls = d.class_name || 'unknown';
    acc[cls] = (acc[cls] || 0) + 1;
    return acc;
  }, {});

  const barData = {
    labels: Object.keys(classCounts),
    datasets: [{
      label: 'Detections',
      data: Object.values(classCounts),
      backgroundColor: 'rgba(0, 212, 255, 0.3)',
      borderColor: 'rgba(0, 212,255, 1)',
      borderWidth: 2,
      borderRadius: 4,
    }]
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#8fa3c7' } },
      title: { display: false },
    },
    scales: {
      x: { ticks: { color: '#8fa3c7' }, grid: { color: 'rgba(0,212,255,0.05)' } },
      y: { ticks: { color: '#8fa3c7', stepSize: 1 }, grid: { color: 'rgba(0,212,255,0.05)' } },
    }
  };

  // --- Map markers ---
  const geoDetections = allDetections.filter(d => d.latitude && d.longitude);
  const mapCenter = geoDetections.length > 0
    ? [geoDetections[0].latitude, geoDetections[0].longitude]
    : [0, 0];

  const decisionColor = (decision) => {
    if (!decision) return '#f5a623';
    const d = decision.toUpperCase();
    if (d === 'CONFIRMED') return '#54d62c';
    if (d === 'REJECTED') return '#ff5370';
    return '#f5a623';
  };

  // Summary stats
  const confirmed = allDetections.filter(d => d.decision?.toUpperCase() === 'CONFIRMED').length;
  const rejected = allDetections.filter(d => d.decision?.toUpperCase() === 'REJECTED').length;
  const avgConf = allDetections.length
    ? (allDetections.reduce((s, d) => s + (d.final_confidence || d.detector_confidence || 0), 0) / allDetections.length * 100).toFixed(1)
    : '0';

  return (
    <div className="reports-layout">
      {/* Summary Cards */}
      <div className="reports-summary">
        {[
          { label: 'Total Jobs', value: jobs.length, color: 'var(--accent-cyan)' },
          { label: 'Total Detections', value: allDetections.length, color: 'var(--text-primary)' },
          { label: 'Confirmed', value: confirmed, color: 'var(--accent-lime)' },
          { label: 'Rejected', value: rejected, color: 'var(--accent-rose)' },
          { label: 'Avg Confidence', value: `${avgConf}%`, color: 'var(--accent-amber)' },
          { label: 'Geotagged', value: geoDetections.length, color: 'var(--accent-violet)' },
        ].map(card => (
          <div className="report-stat-card" key={card.label}>
            <div className="report-stat-value" style={{ color: card.color }}>{loading ? '...' : card.value}</div>
            <div className="report-stat-label">{card.label}</div>
          </div>
        ))}
      </div>

      <div className="reports-body">
        {/* Chart */}
        <div className="reports-panel full-width">
          <div className="section-label">Detections by Class</div>
          <div className="chart-container">
            {!loading && allDetections.length > 0 ? (
              <Bar data={barData} options={barOptions} />
            ) : (
              <div className="panel-empty">{loading ? 'Loading...' : 'No detections yet. Run an analysis first.'}</div>
            )}
          </div>
        </div>

        {/* Job log table */}
        <div className="reports-panel full-width">
          <div className="section-label">All Jobs</div>
          <div className="table-wrap">
            <table className="det-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Status</th>
                  <th>File</th>
                  <th>Message</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(j => (
                  <tr key={j.job_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{j.job_id}</td>
                    <td>
                      <span className={`status-badge status-${j.status?.toLowerCase()}`}>{j.status}</span>
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', maxWidth: 200, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                      {j.input_file_path?.split(/[\\/]/).pop() || '—'}
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{j.message || '—'}</td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{j.created_at ? new Date(j.created_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
