import type { RejectedRow } from '../types/dashboard';

interface Props {
  data: RejectedRow[];
  loading: boolean;
}

export default function RejectedRowsTable({ data, loading }: Props) {
  if (loading) return <div className="table-panel"><h3>Rejected rows by reason</h3><div className="skeleton skeleton-table" /></div>;
  if (data.length === 0) return <div className="table-panel"><h3>Rejected rows by reason</h3><div className="empty-state">No rejected rows.</div></div>;

  return (
    <div className="table-panel">
      <h3>Rejected rows by reason</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Reject Reason</th>
            <th className="text-right">Rows</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr key={i}>
              <td>{r.reject_reason}</td>
              <td className="text-right">{r.rows.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
