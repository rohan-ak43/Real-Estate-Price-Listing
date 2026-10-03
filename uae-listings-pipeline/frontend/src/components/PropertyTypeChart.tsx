import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { PropertyTypeCount } from '../types/dashboard';

interface Props {
  data: PropertyTypeCount[];
}

const COLORS = ['#60a5fa', '#818cf8', '#a78bfa', '#c084fc', '#e879f9', '#f472b6', '#fb7185'];

export default function PropertyTypeChart({ data }: Props) {
  if (data.length === 0) return <div className="empty-state">No data for current filters.</div>;

  return (
    <div className="chart-panel">
      <h3>Listings by property type</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <XAxis dataKey="property_type" tick={{ fill: '#e2e8f0', fontSize: 12 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v: number) => v.toLocaleString()} />
          <Tooltip
            contentStyle={{ background: '#1c2333', border: '1px solid #2d3748', borderRadius: 8, fontSize: 13 }}
            labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
            formatter={(value: number | string) => [Number(value).toLocaleString(), 'Listings']}
          />
          <Bar dataKey="listings" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
