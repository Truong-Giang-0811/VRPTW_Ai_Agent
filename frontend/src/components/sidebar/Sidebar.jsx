import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'

const TABS = [['dispatch', '📋 Điều phối'], ['routes', '🛣 Chi tiết tuyến'], ['history', '🕘 Lịch sử']]

// Khung chứa tab; có thể thu gọn hoàn toàn giống sidebar của ChatGPT.
export default function Sidebar({ open, onToggle, tab, onTab, children }) {
  return (
    <div className={`sidebar-shell ${open ? 'open' : 'collapsed'}`}>
      {open && (
        <aside className="sidebar glass">
          <div className="sidebar-topbar">
            <button
              type="button"
              className="sidebar-toggle"
              onClick={onToggle}
              title="Thu gọn sidebar"
              aria-label="Thu gọn sidebar"
            >
              <PanelLeftClose size={18} strokeWidth={2} />
            </button>
          </div>
          <nav className="tabs">
            {TABS.map(([k, label]) => (
              <button key={k} className={tab === k ? 'on' : ''} onClick={() => onTab(k)}>
                {label}
              </button>
            ))}
          </nav>
          <div className="tab-scroll">{children}</div>
        </aside>
      )}

      {!open && (
        <button
          type="button"
          className="sidebar-toggle sidebar-toggle-collapsed"
          onClick={onToggle}
          title="Mở sidebar"
          aria-label="Mở sidebar"
        >
          <PanelLeftOpen size={18} strokeWidth={2} />
        </button>
      )}
    </div>
  )
}
