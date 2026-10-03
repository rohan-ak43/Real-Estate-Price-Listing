import type { PriceChange } from '../types/dashboard';

interface Props {
  data: PriceChange[];
  loading: boolean;
}

function fmtPrice(v: number): string {
  return v != null ? `AED ${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '-';
}

function fmtDate(raw: string | null): string {
  if (!raw) return '-';
  try {
    return new Date(raw).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return raw;
  }
}

export default function PriceChangesTable({ data, loading }: Props) {
  if (loading) return <div className="table-panel"><h3>Biggest recent price changes</h3><div className="skeleton skeleton-table" /></div>;
  if (data.length === 0) return <div className="table-panel"><h3>Biggest recent price changes</h3><div className="empty-state">No price-change history yet.</div></div>;

  return (
    <div className="table-panel">
      <h3>Biggest recent price changes</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Listing ID</th>
            <th>Community</th>
            <th>Property Type</th>
            <th className="text-right">Old Price</th>
            <th className="text-right">New Price</th>
            <th className="text-right">Change %</th>
            <th>Changed At</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr key={i}>
              <td>{r.listing_id}</td>
              <td>{r.community}</td>
              <td>{r.property_type}</td>
              <td className="text-right">{fmtPrice(r.old_price)}</td>
              <td className="text-right">{fmtPrice(r.new_price)}</td>
              <td className={`text-right ${r.change_pct >= 0 ? 'pct-positive' : 'pct-negative'}`}>
                {r.change_pct >= 0 ? '+' : ''}{r.change_pct.toFixed(1)}%
              </td>
              <td>{fmtDate(r.changed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
