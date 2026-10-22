const PROMPTS = ['Tối ưu lộ trình hôm nay', 'Xe nào tải nặng nhất?', 'Có đơn nào vi phạm khung giờ?', 'So sánh 2 chế độ']
export default function QuickPrompts({ onPick }) {
  return <div className="pills">{PROMPTS.map((p) => <button key={p} className="pill" onClick={() => onPick(p)}>{p}</button>)}</div>
}
