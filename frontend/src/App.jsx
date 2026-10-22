import { useEffect, useState, useCallback } from 'react'
import Navbar from './components/common/Navbar'
import Toast from './components/common/Toast'
import CompareModal from './components/common/CompareModal'
import AddOrderModal from './components/sidebar/widgets/AddOrderModal'
import MapContainer from './components/map/MapContainer'
import Sidebar from './components/sidebar/Sidebar'
import DispatchTab from './components/sidebar/tabs/DispatchTab'
import RoutesDetailTab from './components/sidebar/tabs/RoutesDetailTab'
import HistoryTab from './components/sidebar/tabs/HistoryTab'
import AgentChatDrawer from './components/chat/AgentChatDrawer'
import * as depotsApi from './api/depotsApi'
import * as ordersApi from './api/ordersApi'
import * as vehiclesApi from './api/vehiclesApi'
import { optimizeRoutes, saveRoutePlan, compareModes, listRoutePlans, getRoutePlan } from './api/routesApi'
import { streamChatMessage, getChatThread, resumeAgentAction } from './api/chatApi'
import { DEFAULT_ALGO } from './constants/config'
import DepotManagement from './components/management/DepotManagement'
import OrderManagement from './components/management/OrderManagement'
import VehicleManagement from './components/management/VehicleManagement'

const today = () => {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 10)
}

// Backend có thể trả ngày dạng YYYY-MM-DD hoặc timestamp ISO.
const orderDateKey = (order) => String(order.delivery_date ?? '').slice(0, 10)

export default function App() {
  // ---- state trung tâm: Sidebar, Map và Chat cùng đọc/ghi ở đây
  const [theme, setTheme] = useState('light')
  const [workspace, setWorkspace] = useState('dispatch')
  const [tab, setTab] = useState('dispatch')
  const [date, setDate] = useState(today())
  const [depots, setDepots] = useState([])
  const [depotId, setDepotId] = useState(null)
  const [orders, setOrders] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [algo, setAlgo] = useState(DEFAULT_ALGO)
  const [optimizationResult, setResult] = useState(null)
  const [focusedRouteId, setFocused] = useState(null)
  const [hiddenRoutes, setHidden] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [isSaving, setSaving] = useState(false)
  const [plans, setPlans] = useState([])
  const [toast, setToast] = useState(null)
  const [compare, setCompare] = useState({ open: false, loading: false, data: null })
  const [addOrderOpen, setAddOrderOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [chatHistory, setChatHistory] = useState([
    { role: 'ai', text: 'Xin chào! Mình là trợ lý điều phối VRPTW. Bạn có thể yêu cầu mình tối ưu lộ trình, so sánh thuật toán hoặc giải đáp thông tin đội xe.' },
  ])
  const [thinking, setThinking] = useState(false)
  const [thinkingStatus, setThinkingStatus] = useState(null)
  // Giữ thread_id trong phiên giao diện hiện tại để LangGraph nối tiếp hội thoại.
  const [agentThreadId, setAgentThreadId] = useState(null)
  // Kế hoạch tuyến đường đang được chọn làm ngữ cảnh cho Agent/What-if.
  const [activeRoutePlanId, setActiveRoutePlanId] = useState(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    Promise.all([depotsApi.list(), ordersApi.list(), vehiclesApi.list()])
      .then(([d, o, v]) => {
        setDepots(d)
        setDepotId(d[0]?.id ?? null)
        setOrders(o)
        // Chỉ chọn các đơn thuộc ngày giao đang được chọn trong màn Điều phối.
        setSelectedIds(new Set(o.filter((order) => orderDateKey(order) === date).map((order) => order.id)))
        setVehicles(v)
      })
      .catch((e) => notify('error', e.message))
  }, [])

  useEffect(() => {
    if (tab === 'history') {
      listRoutePlans().then(setPlans).catch((e) => notify('error', e.message))
    }
  }, [tab])

  const notify = (type, message) => setToast({ type, message })
  const closeToast = useCallback(() => setToast(null), [])
  const depot = depots.find((d) => d.id === depotId)
  const filteredOrders = orders.filter((order) => orderDateKey(order) === date)
  const selectedOrders = filteredOrders.filter((order) => selectedIds.has(order.id))

  const handleDateChange = (nextDate) => {
    setDate(nextDate)
    const matchingOrders = orders.filter((order) => orderDateKey(order) === nextDate)
    // Đổi ngày thì danh sách chọn cũng đổi theo, không giữ các đơn của ngày cũ.
    setSelectedIds(new Set(matchingOrders.map((order) => order.id)))
    setResult(null)
  }

  // Payload hoàn chỉnh khớp chuẩn Backend OptimizeRequest
  const buildPayload = () => {
    if (!depot) throw new Error('Vui lòng chọn một kho hàng xuất phát')
    return {
      depot: {
        id: depot.id,
        lat: depot.lat,
        lng: depot.lng,
        ready_time: depot.open || '07:00',
        due_time: depot.close || '18:00',
      },
      customers: selectedOrders.map((o) => ({
        id: o.id,
        lat: o.lat,
        lng: o.lng,
        demand: o.demand,
        ready_time: o.tw_start || '08:00',
        due_time: o.tw_end || '17:00',
        service_time: o.service_min || 10,
      })),
      vehicles: vehicles.map((v) => ({ id: v.id, capacity: v.capacity })),
      vehicle_capacity: algo.capacity || 1000,
      vehicle_number: Math.min(Math.max(1, vehicles.length || 3), 10),
      algorithm: algo.algorithm || 'GA',
      clustering_mode: algo.mode || 'spatiotemporal',
      time_weight: algo.time_weight ?? 0.35,
    }
  }

  const applyResult = (r) => {
    setResult(r)
    setFocused(null)
    setHidden(new Set())
  }

  const handleOptimize = async () => {
    if (selectedIds.size === 0) {
      notify('warning', 'Vui lòng chọn ít nhất 1 đơn hàng để tối ưu')
      return
    }
    setLoading(true)
    try {
      const payload = buildPayload()
      const r = await optimizeRoutes(payload, orders, vehicles)
      // Kết quả tối ưu mới chưa được lưu thành kế hoạch chính thức.
      setActiveRoutePlanId(null)
      applyResult(r)
      setTab('routes')
      notify(
        r.violations ? 'warning' : 'success',
        r.violations ? `Tối ưu hoàn tất: Có ${r.violations} vi phạm khung giờ` : `Tối ưu hoàn tất: ${r.routes.length} xe, ${r.total_distance_km} km`,
      )
    } catch (e) {
      notify('error', e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (result = optimizationResult) => {
    if (!result) return
    setSaving(true)
    try {
      const saved = await saveRoutePlan({ date, depot_id: depotId, result, algo })
      const savedPlanId = saved?.route_plan_id ?? saved?.plan?.id ?? saved?.id ?? null
      if (savedPlanId != null) {
        setActiveRoutePlanId(savedPlanId)
        // Làm mới lịch sử để ID vừa lưu có thể được chọn lại.
        listRoutePlans().then(setPlans).catch(() => { })
        notify('success', `Đã lưu kế hoạch #${savedPlanId} và đặt làm ngữ cảnh cho Agent`)
      } else {
        setActiveRoutePlanId(null)
        notify('warning', 'Yêu cầu lưu đã hoàn tất nhưng API không trả về ID kế hoạch; Agent chưa được gắn với kế hoạch này.')
      }
    } catch (e) {
      notify('error', e.message)
    } finally {
      setSaving(false)
    }
  }

  // Lưu đơn qua API (POST /api/orders/), rồi nạp bản ghi thật từ DB vào state.
  // Lỗi được ném lại để AddOrderModal hiển thị tại form và giữ nguyên dữ liệu đã nhập.
  const handleCreateOrder = async (form) => {
    const created = await ordersApi.create(form)
    setOrders((prev) => [...prev, created])
    setSelectedIds((prev) => new Set(prev).add(created.id))
    setResult(null) // kết quả tối ưu cũ không còn chứa đơn mới
    setAddOrderOpen(false)
    notify('success', `Đã thêm đơn ${created.code}`)
  }

  const handleCreateDepot = async (form) => {
    const created = await depotsApi.create(form)
    setDepots((prev) => [...prev, created])
    if (!depotId) setDepotId(created.id)
    notify('success', `Đã thêm điểm kho ${created.name}`)
  }

  const handleUpdateDepot = async (id, form) => {
    const updated = await depotsApi.update(id, form)
    setDepots((prev) => prev.map((d) => d.id === id ? updated : d))
    notify('success', `Đã cập nhật điểm kho ${updated.name}`)
  }

  const handleDeleteDepot = async (id) => {
    await depotsApi.remove(id)
    setDepots((prev) => prev.filter((d) => d.id !== id))
    if (depotId === id) setDepotId(depots.find((d) => d.id !== id)?.id ?? null)
    notify('success', 'Đã xóa điểm kho')
  }

  const handleCreateVehicle = async (form) => {
    const created = await vehiclesApi.create(form)
    setVehicles((prev) => [...prev, created])
    notify('success', `Đã thêm xe ${created.code}`)
  }

  const handleUpdateVehicle = async (id, form) => {
    const updated = await vehiclesApi.update(id, form)
    setVehicles((prev) => prev.map((v) => v.id === id ? updated : v))
    setResult(null)
    notify('success', `Đã cập nhật xe ${updated.code}`)
  }

  const handleDeleteVehicle = async (id) => {
    await vehiclesApi.remove(id)
    setVehicles((prev) => prev.filter((v) => v.id !== id))
    setResult(null)
    notify('success', 'Đã xóa xe')
  }

  const handleUpdateOrder = async (id, form) => {
    const updated = await ordersApi.update(id, form)
    setOrders((prev) => prev.map((o) => o.id === id ? updated : o))
    setResult(null)
    notify('success', `Đã cập nhật đơn ${updated.code}`)
  }

  const handleDeleteOrder = async (id) => {
    await ordersApi.remove(id)
    setOrders((prev) => prev.filter((o) => o.id !== id))
    setSelectedIds((prev) => { const n = new Set(prev); n.delete(id); return n })
    setResult(null)
    notify('success', 'Đã xóa đơn hàng')
  }

  const handleOrderStatus = async (id, status) => {
    const updated = await ordersApi.updateStatus(id, status)
    setOrders((prev) => prev.map((o) => o.id === id ? updated : o))
    if (status !== 'pending') setResult(null)
    notify('success', `Đã chuyển đơn ${updated.code} sang ${status}`)
  }

  const handleCompare = async () => {
    setCompare({ open: true, loading: true, data: null })
    try {
      const payload = buildPayload()
      const compResult = await compareModes(payload, orders, vehicles)
      setCompare({ open: true, loading: false, data: compResult })
    } catch (e) {
      setCompare({ open: false, loading: false, data: null })
      notify('error', e.message)
    }
  }

  const handleLoadPlan = async (p) => {
    try {
      const r = await getRoutePlan(p.id, orders, vehicles)
      setActiveRoutePlanId(p.id)
      applyResult(r)
      setTab('routes')
      notify('success', `Đã nạp lại kế hoạch #${p.id} (${p.date}) lên bản đồ`)
    } catch (e) {
      notify('error', e.message)
    }
  }

  const toggleRoute = (id) => setHidden((h) => {
    const n = new Set(h)
    n.has(id) ? n.delete(id) : n.add(id)
    return n
  })

  const handleChat = async (text) => {
    const userMessage = text.trim()
    if (!userMessage) return

    setChatHistory((h) => [
      ...h,
      { role: 'user', text: userMessage },
      { role: 'ai', text: '', streaming: true },
    ])
    setThinking(true)
    setThinkingStatus('Đang phân tích yêu cầu...')

    try {
      await streamChatMessage(
        userMessage,
        {
          threadId: agentThreadId,
          activeRoutePlanId,
        },
        {
          onStatus: (statusText) => {
            setThinkingStatus(statusText)
          },
          onToken: (deltaText) => {
            if (!deltaText) return
            setChatHistory((history) => {
              const next = [...history]
              const lastIndex = next.length - 1
              const last = next[lastIndex]

              if (!last || last.role !== 'ai') {
                next.push({ role: 'ai', text: deltaText, streaming: true })
              } else {
                next[lastIndex] = {
                  ...last,
                  text: `${last.text || ''}${deltaText}`,
                  streaming: true,
                }
              }
              return next
            })
          },
          onActionRequired: (payload) => {
            setThinkingStatus(null)
            setChatHistory((history) => {
              const next = [...history]
              const lastIndex = next.length - 1
              const last = next[lastIndex]
              if (last?.role === 'ai') {
                next[lastIndex] = {
                  ...last,
                  text: payload.message || last.text || 'Thao tác này cần bạn xác nhận trước khi thực hiện.',
                  threadId: payload.thread_id || null,
                  requires_action: true,
                  action_data: payload.action_data || null,
                  streaming: false,
                }
              }
              return next
            })
          },
          onDone: (payload) => {
            if (payload.thread_id) setAgentThreadId(payload.thread_id)
            setThinkingStatus(null)
            setChatHistory((history) => {
              const next = [...history]
              const lastIndex = next.length - 1
              const last = next[lastIndex]

              if (last?.role === 'ai') {
                next[lastIndex] = {
                  ...last,
                  text: payload.reply || last.text || 'Agent chưa trả về nội dung phản hồi.',
                  threadId: payload.thread_id || null,
                  requires_action: payload.requires_action || false,
                  action_data: payload.action_data || null,
                  routeResult: payload.routeResult || null,
                  streaming: false,
                  streamError: false,
                }
              }
              return next
            })

            if (payload.routeResult) {
              applyResult(payload.routeResult)
              setTab('routes')
            }
          },
          onError: (error) => {
            setThinkingStatus(null)
            setChatHistory((history) => {
              const next = [...history]
              const lastIndex = next.length - 1
              const last = next[lastIndex]
              if (last?.role === 'ai') {
                next[lastIndex] = {
                  ...last,
                  streaming: false,
                  streamError: true,
                }
              }
              return next
            })
            notify('error', error.message || 'Kết nối với Agent bị gián đoạn')
          },
        },
      )
    } catch {
      // onError đã cập nhật UI; không cần thêm message lỗi thứ hai.
    } finally {
      setThinking(false)
      setThinkingStatus(null)
    }
  }

  const handleActionResponse = async (threadId, approved, messageIndex) => {
    const targetThreadId = threadId || agentThreadId
    if (!targetThreadId) {
      notify('error', 'Không tìm thấy ID phiên hội thoại để xác nhận.')
      return
    }

    // Đánh dấu thẻ hành động đã được giải quyết
    setChatHistory((history) =>
      history.map((msg, idx) => {
        if (idx === messageIndex) {
          return {
            ...msg,
            action_resolved: approved ? 'approved' : 'rejected',
          }
        }
        return msg
      })
    )

    setThinking(true)
    setThinkingStatus(approved ? 'Đang thực thi thao tác đã phê duyệt...' : 'Đang hủy thao tác...')

    try {
      const res = await resumeAgentAction(
        targetThreadId,
        approved,
        approved ? 'Đã chấp thuận.' : 'Người dùng đã từ chối thao tác.',
        { activeRoutePlanId, userId: 'default' }
      )

      if (res.threadId) setAgentThreadId(res.threadId)

      setChatHistory((history) => [
        ...history,
        {
          role: 'ai',
          text: res.text || (approved ? 'Đã thực hiện xong thao tác.' : 'Đã hủy bỏ thao tác theo yêu cầu của bạn.'),
          threadId: res.threadId,
          requires_action: res.requiresAction,
          action_data: res.actionData,
          routeResult: res.routeResult,
        },
      ])

      if (res.routeResult) {
        applyResult(res.routeResult)
        setTab('routes')
      }
    } catch (e) {
      notify('error', e.message || 'Lỗi khi tiếp tục xử lý thao tác')
    } finally {
      setThinking(false)
      setThinkingStatus(null)
    }
  }

  const handleNewChat = () => {
    setAgentThreadId(null)
    setThinkingStatus(null)
    setChatHistory([
      { role: 'ai', text: 'Xin chào! Mình là trợ lý điều phối VRPTW. Bạn có thể yêu cầu mình tối ưu lộ trình, so sánh thuật toán hoặc giải đáp thông tin đội xe.' },
    ])
    notify('info', 'Đã bắt đầu cuộc trò chuyện mới')
  }

  const handleSelectThread = async (threadId) => {
    try {
      setThinking(true)
      const data = await getChatThread(threadId)
      if (data && Array.isArray(data.messages)) {
        setChatHistory(data.messages)
        setAgentThreadId(threadId)
        notify('success', 'Đã tải lại cuộc trò chuyện từ lịch sử')
      }
    } catch (e) {
      notify('error', e.message || 'Không thể tải cuộc trò chuyện')
    } finally {
      setThinking(false)
    }
  }

  return (
    <div className="app">
      <Navbar
        result={optimizationResult}
        theme={theme}
        workspace={workspace}
        onWorkspace={setWorkspace}
        onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        canCompare={selectedIds.size > 0}
        onCompare={handleCompare}
      />
      <div className={`main ${workspace !== 'dispatch' ? 'management-main' : ''}`}>
        {workspace === 'dispatch' ? <>
          <Sidebar
            open={sidebarOpen}
            onToggle={() => setSidebarOpen((open) => !open)}
            tab={tab}
            onTab={setTab}
          >
            {tab === 'dispatch' && <DispatchTab date={date} onDate={handleDateChange} depots={depots} depotId={depotId} onDepot={setDepotId} orders={filteredOrders} selectedIds={selectedIds} onSelect={setSelectedIds} algo={algo} onAlgo={setAlgo} loading={loading} saving={isSaving} hasResult={!!optimizationResult} onOptimize={handleOptimize} onSave={() => handleSave()} onAddOrder={() => setAddOrderOpen(true)} />}
            {tab === 'routes' && <RoutesDetailTab result={optimizationResult} focusedRouteId={focusedRouteId} onFocusRoute={setFocused} />}
            {tab === 'history' && <HistoryTab plans={plans} onLoadPlan={handleLoadPlan} />}
          </Sidebar>
          <MapContainer theme={theme} depot={depot} orders={selectedOrders} result={optimizationResult} focusedRouteId={focusedRouteId} hiddenRoutes={hiddenRoutes} onToggleRoute={toggleRoute} onFocusRoute={setFocused} />
        </> : workspace === 'depots' ? <DepotManagement depots={depots} onCreate={handleCreateDepot} onUpdate={handleUpdateDepot} onDelete={handleDeleteDepot} notify={notify} />
          : workspace === 'orders' ? <OrderManagement orders={orders} onCreate={handleCreateOrder} onUpdate={handleUpdateOrder} onDelete={handleDeleteOrder} onStatus={handleOrderStatus} notify={notify} />
            : <VehicleManagement vehicles={vehicles} onCreate={handleCreateVehicle} onUpdate={handleUpdateVehicle} onDelete={handleDeleteVehicle} notify={notify} />}
      </div>
      <AgentChatDrawer
        open={chatOpen}
        onToggle={() => setChatOpen(!chatOpen)}
        messages={chatHistory}
        thinking={thinking}
        thinkingStatus={thinkingStatus}
        onSend={handleChat}
        onViewRoute={(r) => { setActiveRoutePlanId(null); applyResult(r); setTab('routes') }}
        onSaveRoute={handleSave}
        threadId={agentThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        onActionResponse={handleActionResponse}
      />
      <CompareModal
        {...compare}
        onClose={() => setCompare({ open: false, loading: false, data: null })}
        onPick={(r) => { setActiveRoutePlanId(null); applyResult(r); setTab('routes') }}
      />
      <AddOrderModal
        open={addOrderOpen}
        defaultDate={date}
        anchor={depot ? [depot.lat, depot.lng] : null}
        onClose={() => setAddOrderOpen(false)}
        onSubmit={handleCreateOrder}
      />
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}
