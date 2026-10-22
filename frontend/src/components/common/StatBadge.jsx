export default function StatBadge({ icon, label, value, tone = 'default' }) {
  return (
    <div className={`stat-badge tone-${tone}`}>
      {icon && <span className="stat-icon">{icon}</span>}
      <div><div className="stat-value">{value}</div><div className="stat-label">{label}</div></div>
    </div>
  )
}
