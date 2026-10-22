export default function ManagementShell({ title, description, actions, children }) {
  return (
    <section className="management-shell">
      <div className="management-head glass">
        <div>
          <div className="eyebrow">QUẢN TRỊ VẬN HÀNH</div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <div className="management-head-actions">{actions}</div>
      </div>
      {children}
    </section>
  )
}

export function KpiCard({ label, value, hint }) {
  return <div className="kpi-card glass"><span>{label}</span><strong>{value}</strong>{hint && <small>{hint}</small>}</div>
}
