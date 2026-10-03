import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import type { PriceTrend } from '../types/dashboard';

interface Props {
  data: PriceTrend[];
}

export default function PriceTrendChart({ data }: Props) {
  if (data.length === 0) return <div className="empty-state">No trend data for current filters.</div>;

  return (
    <div className="chart-panel chart-full">
      <h3>Price per sqft trend (by month listed)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ left: 10, right: 30, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="year_month" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickFormatter={(v: number) => v.toLocaleString()}
            label={{ value: 'Average AED / sqft', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12, dx: -5 }}
          />
          <Tooltip
            contentStyle={{ background: '#1c2333', border: '1px solid #2d3748', borderRadius: 8, fontSize: 13 }}
            labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
            formatter={(value: number | string) => [`AED ${Number(value).toLocaleString()}`, 'Avg AED/sqft']}
          />
          <Line
            type="monotone"
            dataKey="avg_price_per_sqft"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={{ fill: '#60a5fa', r: 3 }}
            activeDot={{ r: 5, fill: '#93c5fd' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
