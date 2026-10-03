import type { DataQualityResult } from '../types/dashboard';

interface Props {
  data: DataQualityResult[];
  loading: boolean;
}

function severityBadge(sev: string) {
  const cls =
    sev.toLowerCase() === 'error'
      ? 'badge badge-error'
      : sev.toLowerCase() === 'warning'
        ? 'badge badge-warning'
        : 'badge badge-info';
  return <span className={cls}>{sev}</span>;
}

export default function DataQualityTable({ data, loading }: Props) {
  if (loading) return <div className="table-panel"><h3>Latest data-quality results</h3><div className="skeleton skeleton-table" /></div>;
  if (data.length === 0) return <div className="table-panel"><h3>Latest data-quality results</h3><div className="empty-state">No DQ results yet.</div></div>;

  return (
    <div className="table-panel">
      <h3>Latest data-quality results</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Check Name</th>
            <th>Severity</th>
            <th>Passed</th>
            <th>Detail</th>
            <th>Run ID</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr key={i}>
              <td>{r.check_name}</td>
              <td>{severityBadge(r.severity)}</td>
              <td>{r.passed ? <span className="pass-icon">✓ Passed</span> : <span className="fail-icon">✕ Failed</span>}</td>
              <td>{r.detail || '-'}</td>
              <td>{r.run_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
