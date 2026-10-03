import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { CommunityPrice } from '../types/dashboard';

interface Props {
  data: CommunityPrice[];
}

const BAR_COLOR = '#60a5fa';

export default function CommunityPriceChart({ data }: Props) {
  if (data.length === 0) return <div className="empty-state">No data for current filters.</div>;

  // Show top 25 communities max to keep the chart readable
  const sliced = data.slice(0, 25);

  return (
    <div className="chart-panel">
      <h3>Median price by community (min. 20 listings)</h3>
      <ResponsiveContainer width="100%" height={Math.max(280, sliced.length * 28)}>
        <BarChart data={sliced} layout="vertical" margin={{ left: 10, right: 30, top: 5, bottom: 5 }}>
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v: number) => v.toLocaleString()} />
          <YAxis
            type="category"
            dataKey="community"
            width={150}
            tick={{ fill: '#e2e8f0', fontSize: 12 }}
            interval={0}
          />
          <Tooltip
            contentStyle={{ background: '#1c2333', border: '1px solid #2d3748', borderRadius: 8, fontSize: 13 }}
            labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
            formatter={(value) => [`AED ${Number(value ?? 0).toLocaleString()}`, 'Median price']}
          />
          <Bar dataKey="median_price" radius={[0, 4, 4, 0]}>
            {sliced.map((_, i) => (
              <Cell key={i} fill={BAR_COLOR} fillOpacity={1 - i * 0.02} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
