interface KPICardProps {
  label: string;
  value: string;
}

export default function KPICard({ label, value }: KPICardProps) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}
