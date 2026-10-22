import StatBadge from './StatBadge'

const NAV = [
  ['dispatch', '🚚 Điều phối'],
  ['depots', '🏭 Điểm kho'],
  ['orders', '📦 Đơn đã nhận'],
  ['vehicles', '🚛 Quản lý xe'],
]

export default function Navbar({ result, theme, onToggleTheme, onCompare, canCompare, workspace, onWorkspace }) {
  return (
    <header className="navbar glass">
      <div className="brand"><span className="logo">🚚</span><b>VRPTW</b><span className="muted">Dispatch Console</span></div>
      <nav className="main-nav">{NAV.map(([key, label]) => <button key={key} className={workspace === key ? 'active' : ''} onClick={() => onWorkspace(key)}>{label}</button>)}</nav>
      <div className="nav-stats">
        {result ? <><StatBadge icon="📏" label="Quãng đường" value={`${result.total_distance_km} km`} /><StatBadge icon="⏱" label="Thời gian" value={`${result.total_time_min} ph`} /><StatBadge icon="🚚" label="Số xe" value={result.routes.length} /></> : <span className="muted">Chưa có kết quả tối ưu</span>}
      </div>
      <div className="nav-actions"><button className="btn" disabled={!canCompare} onClick={onCompare}>⚖ So sánh</button><button className="icon-btn" onClick={onToggleTheme} title="Đổi giao diện">{theme === 'dark' ? '☀️' : '🌙'}</button></div>
    </header>
  )
}
