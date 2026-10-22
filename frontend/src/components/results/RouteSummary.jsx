import Icon from "../ui/Icon";

function formatDuration(minutes) {
  const value = Number(minutes);
  if (!Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  const hours = Math.floor(rounded / 60);
  const mins = rounded % 60;
  return hours > 0 ? `${hours}h ${mins}m` : `${mins} phút`;
}

function formatNumber(value, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n)
    ? n.toLocaleString("vi-VN", { maximumFractionDigits: digits })
    : "—";
}

export default function RouteSummary({ result, title = "Phương án hiện tại", modeLabel }) {
  if (!result) return null;

  return (
    <section className="results-card">
      <div className="results-header">
        <div>
          <div className="eyebrow">KẾT QUẢ TỐI ƯU</div>
          <h3>{title}</h3>
        </div>
        <span className="success-pill">
          <Icon name="check" size={13} /> {modeLabel || result.clustering_mode_label || "Đã tối ưu"}
        </span>
      </div>

      <div className="metrics-grid">
        <div className="metric metric-primary">
          <span>Tổng quãng đường</span>
          <strong>
            {formatNumber(result.total_distance_km)}
            <small> km</small>
          </strong>
        </div>

        <div className="metric metric-primary">
          <span>Tổng thời gian</span>
          <strong title={`${formatNumber(result.total_duration_min, 1)} phút`}>
            {formatDuration(result.total_duration_min)}
          </strong>
        </div>

        <div className="metric metric-primary">
          <span>Tổng thời gian chờ</span>
          <strong title={`${formatNumber(result.total_waiting_time_min, 1)} phút`}>
            {formatDuration(result.total_waiting_time_min)}
          </strong>
        </div>

        <div className="metric">
          <span>Xe sử dụng</span>
          <strong>
            {result.vehicle_count ?? result.routes?.length ?? "—"}
            <small> xe</small>
          </strong>
        </div>
      </div>

      <div className="results-mini-row">
        <span className="results-mini-chip">Cụm: {result.clustering_mode_label || result.clustering_mode || "—"}</span>
        <span className="results-mini-chip">Xử lý: {formatNumber(result.process_time_ms, 1)} ms</span>
      </div>

      {result.routing_warning && (
        <div className="routing-warning">
          <Icon name="info" size={14} />
          <span>{result.routing_warning}</span>
        </div>
      )}
    </section>
  );
}
