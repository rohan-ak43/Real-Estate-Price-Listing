import type { PipelineRun } from '../types/dashboard';

interface Props {
  data: PipelineRun[];
  loading: boolean;
}

function fmtTs(raw: string | null): string {
  if (!raw) return '-';
  try {
    return new Date(raw).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return raw;
  }
}

export default function PipelineRunsTable({ data, loading }: Props) {
  if (loading) return <div className="table-panel"><h3>Pipeline runs</h3><div className="skeleton skeleton-table" /></div>;
  if (data.length === 0) return <div className="table-panel"><h3>Pipeline runs</h3><div className="empty-state">No pipeline runs recorded.</div></div>;

  // Dynamically pick columns from the first row
  const columns = Object.keys(data[0]);

  return (
    <div className="table-panel">
      <h3>Pipeline runs</h3>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => {
                const val = (row as unknown as Record<string, unknown>)[col];
                const display =
                  col.endsWith('_at') && typeof val === 'string'
                    ? fmtTs(val)
                    : val != null
                      ? String(val)
                      : '-';
                return <td key={col}>{display}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
