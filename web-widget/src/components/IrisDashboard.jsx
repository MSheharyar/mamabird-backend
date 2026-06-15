import { useState, useEffect } from 'react'
import axios from 'axios'
import Icon from './Icon'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATUS_META = {
  active:       { label: 'Active',       bg: '#E8F5E4', color: '#3A7030', dot: '#4A8B3F' },
  trial:        { label: 'Trial',        bg: '#EBF6FC', color: '#4A96BC', dot: '#6EB4D4' },
  grace_period: { label: 'Grace',        bg: '#FFFBEA', color: '#7A5C00', dot: '#F5C200' },
  cancelled:    { label: 'Cancelled',    bg: '#FFF0F0', color: '#A82020', dot: '#CC2929' },
  expired:      { label: 'Expired',      bg: '#F5F5F5', color: '#888',    dot: '#bbb' },
}

const PLAN_LABEL = { individual: 'Individual', premium: 'Premium', classroom: 'Classroom' }

function StatCard({ icon, label, value, color, bg, suffix = '' }) {
  return (
    <div style={{
      background: 'white', borderRadius: '16px', padding: '20px 18px',
      boxShadow: '0 3px 14px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0',
      borderTop: `4px solid ${color}`, flex: '1', minWidth: '130px',
    }}>
      <div style={{
        width: '42px', height: '42px', borderRadius: '12px', background: bg,
        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px',
      }}>
        <Icon name={icon} size={20} color={color} />
      </div>
      <div style={{ fontSize: '28px', fontWeight: 800, color, lineHeight: 1 }}>
        {value}{suffix}
      </div>
      <div style={{ fontSize: '11px', color: '#aaa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: '5px' }}>
        {label}
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const m = STATUS_META[status] || { label: status || '—', bg: '#F5F5F5', color: '#888', dot: '#bbb' }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      background: m.bg, color: m.color, padding: '3px 10px',
      borderRadius: '12px', fontSize: '11px', fontWeight: 800,
    }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: m.dot, display: 'inline-block' }} />
      {m.label}
    </span>
  )
}

function ChildCard({ child, msgLimit }) {
  const used = child.messages_used || 0
  const limit = msgLimit || 400
  const pct = Math.min(100, Math.round(used / limit * 100))
  const barColor = pct > 80 ? '#CC2929' : pct > 55 ? '#F5C200' : '#4A8B3F'
  const acc = child.accuracy_pct || 0
  const accColor = acc >= 80 ? '#4A8B3F' : acc >= 50 ? '#B8860B' : '#CC2929'
  const lastActive = child.last_active
    ? new Date(child.last_active).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : 'Never'

  return (
    <div style={{
      background: '#FAFAFA', borderRadius: '14px', padding: '16px',
      border: '1px solid #F0F0F0',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: '15px', color: '#1E1E1E' }}>{child.child_name}</div>
          <div style={{ fontSize: '12px', color: '#999', fontWeight: 600, marginTop: '2px' }}>
            {child.age ? `Age ${child.age}` : ''}
            {child.grade ? (child.age ? ` · ${child.grade}` : child.grade) : ''}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: '#bbb', fontWeight: 600 }}>Last active</div>
          <div style={{ fontSize: '12px', fontWeight: 800, color: '#555' }}>{lastActive}</div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
        {[
          { label: 'Sessions', value: child.total_sessions, icon: 'clock', color: '#6EB4D4' },
          { label: 'Correct', value: child.total_correct, icon: 'check-circle', color: '#4A8B3F' },
          { label: 'Accuracy', value: `${acc}%`, icon: 'target', color: accColor },
          { label: 'Badges', value: child.badges_earned, icon: 'award', color: '#F5C200' },
        ].map(s => (
          <div key={s.label} style={{
            background: 'white', borderRadius: '10px', padding: '10px 8px',
            textAlign: 'center', border: '1px solid #F0F0F0',
          }}>
            <Icon name={s.icon} size={14} color={s.color} />
            <div style={{ fontSize: '16px', fontWeight: 800, color: s.color, marginTop: '4px', lineHeight: 1 }}>{s.value}</div>
            <div style={{ fontSize: '10px', color: '#bbb', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.3px', marginTop: '3px' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Message usage bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, color: '#888', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Icon name="message" size={11} color="#888" /> Messages
          </span>
          <span style={{ fontSize: '11px', fontWeight: 800, color: barColor }}>{used} / {limit} ({pct}%)</span>
        </div>
        <div style={{ background: '#EBEBEB', borderRadius: '6px', height: '6px', overflow: 'hidden' }}>
          <div style={{ height: '100%', borderRadius: '6px', background: barColor, width: `${pct}%`, transition: 'width 0.5s ease' }} />
        </div>
      </div>

      {child.last_subject && (
        <div style={{ marginTop: '10px', fontSize: '11px', color: '#888', fontWeight: 600 }}>
          Last subject: <span style={{ color: '#6EB4D4', fontWeight: 800, textTransform: 'capitalize' }}>{child.last_subject}</span>
        </div>
      )}
    </div>
  )
}

function ParentRow({ parent, onExtendTrial, onCancel }) {
  const [expanded, setExpanded] = useState(false)
  const status = parent.subscription_status
  const joined = parent.created_at
    ? new Date(parent.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—'
  const trialEnd = parent.trial_ends_at
    ? new Date(parent.trial_ends_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : null
  const msgLimit = parent.subscription_plan === 'classroom' ? 6000
    : parent.subscription_plan === 'premium' ? 1000 : 400

  const isTrialExpiring = trialEnd && status === 'trial' &&
    (new Date(parent.trial_ends_at) - new Date()) < 3 * 24 * 60 * 60 * 1000

  return (
    <div style={{
      background: 'white', borderRadius: '16px', marginBottom: '10px',
      border: isTrialExpiring ? '2px solid #F5C200' : '1px solid #F0F0F0',
      boxShadow: expanded ? '0 4px 20px rgba(0,0,0,0.09)' : '0 2px 8px rgba(0,0,0,0.05)',
      transition: 'box-shadow 0.2s',
      overflow: 'hidden',
    }}>
      {/* Parent header row */}
      <div
        onClick={() => setExpanded(e => !e)}
        style={{ padding: '16px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '14px' }}
      >
        {/* Avatar */}
        <div style={{
          width: '40px', height: '40px', borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg, #EBF6FC, #D6EEFB)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '2px solid rgba(110,180,212,0.3)',
        }}>
          <Icon name="user" size={18} color="#6EB4D4" />
        </div>

        {/* Email + plan */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 800, fontSize: '14px', color: '#1E1E1E', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {parent.email}
            {isTrialExpiring && (
              <span style={{ fontSize: '10px', background: '#FFFBEA', color: '#7A5C00', border: '1px solid #F5C200', borderRadius: '8px', padding: '2px 7px', fontWeight: 800 }}>
                Trial expiring soon
              </span>
            )}
          </div>
          <div style={{ fontSize: '12px', color: '#888', fontWeight: 600, marginTop: '2px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {PLAN_LABEL[parent.subscription_plan] || 'No plan'} · Joined {joined}
            {trialEnd && status === 'trial' && <span>· Trial ends {trialEnd}</span>}
          </div>
        </div>

        {/* Status badge */}
        <StatusBadge status={status} />

        {/* Children count */}
        <div style={{ textAlign: 'center', minWidth: '52px' }}>
          <div style={{ fontSize: '18px', fontWeight: 800, color: '#6EB4D4' }}>{parent.children.length}</div>
          <div style={{ fontSize: '10px', color: '#bbb', fontWeight: 700, textTransform: 'uppercase' }}>Children</div>
        </div>

        {/* 30d cost */}
        <div style={{ textAlign: 'center', minWidth: '60px' }}>
          <div style={{ fontSize: '14px', fontWeight: 800, color: '#CC2929' }}>${parent.usage_30d?.cost_usd?.toFixed(4) || '0.0000'}</div>
          <div style={{ fontSize: '10px', color: '#bbb', fontWeight: 700, textTransform: 'uppercase' }}>API/30d</div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }} onClick={e => e.stopPropagation()}>
          <button
            onClick={() => onExtendTrial(parent.id, parent.email)}
            style={{
              padding: '6px 11px', background: 'linear-gradient(135deg, #6EB4D4, #4A96BC)',
              color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer',
              fontSize: '11px', fontWeight: 800, fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', gap: '4px',
            }}
          >
            <Icon name="refresh" size={11} color="white" /> Extend
          </button>
          <button
            onClick={() => onCancel(parent.id, parent.email)}
            style={{
              padding: '6px 11px', background: 'white', color: '#CC2929',
              border: '1.5px solid #CC292944', borderRadius: '8px', cursor: 'pointer',
              fontSize: '11px', fontWeight: 800, fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', gap: '4px',
            }}
          >
            <Icon name="ban" size={11} color="#CC2929" /> Cancel
          </button>
        </div>

        {/* Expand chevron */}
        <div style={{ color: '#ccc', fontSize: '12px', marginLeft: '4px', transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'none' }}>▼</div>
      </div>

      {/* Expanded children section */}
      {expanded && (
        <div style={{ padding: '0 20px 20px', borderTop: '1px solid #F5F5F5' }}>
          <div style={{ paddingTop: '16px' }}>
            {parent.children.length === 0 ? (
              <div style={{ color: '#ccc', fontSize: '13px', fontWeight: 600, textAlign: 'center', padding: '20px' }}>
                No child profiles yet.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                {parent.children.map(child => (
                  <ChildCard key={child.id} child={child} msgLimit={msgLimit} />
                ))}
              </div>
            )}

            {/* Usage summary */}
            <div style={{ marginTop: '14px', padding: '12px 16px', background: '#FAFAFA', borderRadius: '10px', display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
              <div style={{ fontSize: '12px', color: '#888', fontWeight: 600 }}>
                <span style={{ fontWeight: 800, color: '#333' }}>{parent.usage_30d?.messages || 0}</span> API calls in last 30 days
              </div>
              <div style={{ fontSize: '12px', color: '#888', fontWeight: 600 }}>
                <span style={{ fontWeight: 800, color: '#CC2929' }}>${parent.usage_30d?.cost_usd?.toFixed(4) || '0.0000'}</span> cost in last 30 days
              </div>
              {parent.subscription_ends_at && (
                <div style={{ fontSize: '12px', color: '#888', fontWeight: 600 }}>
                  Subscription ends: <span style={{ fontWeight: 800, color: '#CC2929' }}>
                    {new Date(parent.subscription_ends_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function IrisDashboard({ token, onLogout }) {
  const [data, setData] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [extendModal, setExtendModal] = useState(null)
  const [extendDays, setExtendDays] = useState(14)
  const [actionMsg, setActionMsg] = useState('')
  const [actionOk, setActionOk] = useState(true)

  const headers = { Authorization: `Bearer ${token}` }

  const loadData = async () => {
    setLoading(true)
    try {
      const [detailRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/admin/parents-detailed`, { headers }),
        axios.get(`${API_URL}/admin/stats`, { headers }),
      ])
      setData(detailRes.data)
      setStats(statsRes.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const doExtendTrial = async () => {
    if (!extendModal) return
    try {
      await axios.put(`${API_URL}/admin/users/${extendModal.userId}/extend-trial`, { days: extendDays }, { headers })
      setActionMsg(`Trial extended by ${extendDays} days for ${extendModal.email}`)
      setActionOk(true)
      setExtendModal(null)
      loadData()
    } catch (e) {
      setActionMsg(e.response?.data?.detail || 'Failed to extend trial')
      setActionOk(false)
    }
  }

  const doCancel = async (userId, email) => {
    if (!window.confirm(`Cancel subscription for ${email}? This cannot be undone from the UI.`)) return
    try {
      await axios.put(`${API_URL}/admin/users/${userId}/cancel`, {}, { headers })
      setActionMsg(`Subscription cancelled for ${email}`)
      setActionOk(true)
      loadData()
    } catch (e) {
      setActionMsg(e.response?.data?.detail || 'Failed to cancel')
      setActionOk(false)
    }
  }

  const summary = data?.summary || {}
  const parents = data?.parents || []

  const filtered = parents.filter(p => {
    const matchSearch = !search || p.email.toLowerCase().includes(search.toLowerCase()) ||
      p.children.some(c => c.child_name?.toLowerCase().includes(search.toLowerCase()))
    const matchStatus = statusFilter === 'all' || p.subscription_status === statusFilter
    return matchSearch && matchStatus
  })

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', width: '100%', display: 'flex', alignItems: 'center',
        justifyContent: 'center', flexDirection: 'column', gap: '14px',
      }}>
        <div style={{ animation: 'float 2s ease-in-out infinite', fontSize: '52px' }}>🐦</div>
        <div style={{ color: '#888', fontWeight: 700, fontSize: '14px' }}>Loading Iris Dashboard...</div>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh', width: '100%', fontFamily: 'inherit',
      background: 'linear-gradient(160deg, #87CEEB 0%, #C8E9F8 60%, #E0F4FF 100%)',
    }}>
      {/* ─── Top Nav ─────────────────────────────────────────────────────── */}
      <div style={{
        background: 'white', borderBottom: '2px solid #F0F0F0',
        padding: '0 32px', height: '64px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        boxShadow: '0 2px 12px rgba(0,0,0,0.07)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ fontSize: '28px' }}>🐦</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '16px', color: '#CC2929', letterSpacing: '-0.2px' }}>MamaBird Admin</div>
            <div style={{ fontSize: '11px', color: '#bbb', fontWeight: 700 }}>Iris Dashboard · Client Management</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 14px', background: '#FFF0F0', borderRadius: '20px',
            border: '1px solid rgba(204,41,41,0.15)',
          }}>
            <Icon name="shield" size={14} color="#CC2929" />
            <span style={{ fontWeight: 800, fontSize: '13px', color: '#CC2929' }}>iris@threebabybirdies.com</span>
          </div>
          <button
            onClick={onLogout}
            style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              padding: '7px 14px', background: 'none', border: '1.5px solid #E8E8E8',
              borderRadius: '10px', color: '#888', fontWeight: 800, fontSize: '12px',
              cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#CC2929'; e.currentTarget.style.color = '#CC2929' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#E8E8E8'; e.currentTarget.style.color = '#888' }}
          >
            <Icon name="x" size={12} color="currentColor" />
            Log out
          </button>
        </div>
      </div>

      {/* ─── Main Content ─────────────────────────────────────────────────── */}
      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '32px 24px' }}>

        {/* Action message */}
        {actionMsg && (
          <div style={{
            background: actionOk ? '#E8F5E4' : '#FFF0F0',
            color: actionOk ? '#3A7030' : '#A82020',
            padding: '11px 18px', borderRadius: '12px', marginBottom: '20px',
            fontSize: '13px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
              <Icon name={actionOk ? 'check' : 'alert'} size={14} color={actionOk ? '#3A7030' : '#A82020'} />
              {actionMsg}
            </span>
            <button onClick={() => setActionMsg('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>
              <Icon name="x" size={15} color="currentColor" />
            </button>
          </div>
        )}

        {/* ─── Stats Row ─────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '28px', flexWrap: 'wrap' }}>
          <StatCard icon="users"       label="Total Parents"    value={summary.total_parents || 0}   color="#6EB4D4" bg="#EBF6FC" />
          <StatCard icon="user"        label="Total Children"   value={summary.total_children || 0}  color="#CC2929" bg="#FFF0F0" />
          <StatCard icon="check-circle" label="Active Subs"     value={summary.active_subscribers || 0} color="#4A8B3F" bg="#E8F5E4" />
          <StatCard icon="clock"       label="Trial Users"      value={summary.trial_users || 0}     color="#F5C200" bg="#FFFBEA" />
          <StatCard icon="bar-chart"   label="Total Sessions"   value={summary.total_sessions || 0}  color="#6EB4D4" bg="#EBF6FC" />
          <StatCard icon="target"      label="Avg Accuracy"     value={summary.overall_accuracy || 0} color="#4A8B3F" bg="#E8F5E4" suffix="%" />
        </div>

        {/* ─── Parents & Children ────────────────────────────────────────── */}
        <div style={{
          background: 'white', borderRadius: '20px', padding: '24px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
        }}>
          {/* Section header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#1E1E1E', display: 'flex', alignItems: 'center', gap: '9px' }}>
              <Icon name="users" size={20} color="#CC2929" />
              Parents & Children
              <span style={{ fontSize: '13px', color: '#bbb', fontWeight: 700 }}>({filtered.length} shown)</span>
            </h2>
            <button
              onClick={loadData}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px',
                background: 'linear-gradient(135deg, #6EB4D4, #4A96BC)', color: 'white',
                border: 'none', borderRadius: '10px', cursor: 'pointer',
                fontFamily: 'inherit', fontWeight: 800, fontSize: '12px',
              }}
            >
              <Icon name="refresh" size={13} color="white" /> Refresh
            </button>
          </div>

          {/* Search + filter */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
              <div style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}>
                <Icon name="user" size={14} color="#bbb" />
              </div>
              <input
                placeholder="Search by parent email or child name..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  width: '100%', padding: '9px 12px 9px 34px',
                  border: '2px solid #E8E8E8', borderRadius: '10px',
                  fontFamily: 'inherit', fontSize: '13px', fontWeight: 600,
                  background: '#FAFAFA', outline: 'none',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {['all', 'trial', 'active', 'grace_period', 'cancelled'].map(f => (
                <button
                  key={f}
                  onClick={() => setStatusFilter(f)}
                  style={{
                    padding: '7px 14px', border: 'none', borderRadius: '20px', cursor: 'pointer',
                    fontSize: '12px', fontWeight: 800, fontFamily: 'inherit', transition: 'all 0.15s',
                    background: statusFilter === f ? 'linear-gradient(135deg, #CC2929, #A82020)' : '#F0F0F0',
                    color: statusFilter === f ? 'white' : '#666',
                    boxShadow: statusFilter === f ? '0 2px 8px rgba(204,41,41,0.3)' : 'none',
                  }}
                >
                  {f === 'all' ? 'All' : f === 'grace_period' ? 'Grace' : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Parent list */}
          {filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0', color: '#ccc', fontSize: '14px', fontWeight: 700 }}>
              <div style={{ fontSize: '40px', marginBottom: '10px' }}>🔍</div>
              No parents match your search.
            </div>
          ) : (
            filtered.map(parent => (
              <ParentRow
                key={parent.id}
                parent={parent}
                onExtendTrial={(userId, email) => { setExtendModal({ userId, email }); setExtendDays(14) }}
                onCancel={doCancel}
              />
            ))
          )}
        </div>
      </div>

      {/* ─── Extend Trial Modal ───────────────────────────────────────────── */}
      {extendModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000,
          backdropFilter: 'blur(4px)',
        }}>
          <div style={{
            background: 'white', borderRadius: '22px', overflow: 'hidden',
            width: '380px', boxShadow: '0 24px 64px rgba(0,0,0,0.2)',
            animation: 'fadeSlideIn 0.2s ease',
          }}>
            <div style={{ background: 'linear-gradient(135deg, #6EB4D4, #4A96BC)', padding: '20px 26px' }}>
              <h3 style={{ color: 'white', margin: 0, fontWeight: 800, fontSize: '18px', display: 'flex', alignItems: 'center', gap: '9px' }}>
                <Icon name="refresh" size={18} color="white" />
                Extend Trial
              </h3>
              <p style={{ color: 'rgba(255,255,255,0.85)', margin: '5px 0 0', fontSize: '13px', fontWeight: 600 }}>
                {extendModal.email}
              </p>
            </div>
            <div style={{ padding: '26px' }}>
              <label style={{ fontSize: '12px', fontWeight: 800, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Days to add (1–30)
              </label>
              <input
                type="number" min={1} max={30} value={extendDays}
                onChange={e => setExtendDays(Math.min(30, Math.max(1, Number(e.target.value))))}
                style={{
                  display: 'block', width: '100%', margin: '8px 0 24px',
                  padding: '13px 16px', borderRadius: '12px', border: '2px solid #E8E8E8',
                  fontFamily: 'inherit', fontSize: '22px', fontWeight: 800,
                  outline: 'none', color: '#333', textAlign: 'center',
                }}
              />
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={doExtendTrial} style={{
                  flex: 1, padding: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px',
                  background: 'linear-gradient(135deg, #4A8B3F, #3A7030)',
                  color: 'white', border: 'none', borderRadius: '12px',
                  cursor: 'pointer', fontFamily: 'inherit', fontWeight: 800, fontSize: '14px',
                  boxShadow: '0 4px 12px rgba(74,139,63,0.3)',
                }}>
                  <Icon name="check" size={15} color="white" /> Confirm
                </button>
                <button onClick={() => setExtendModal(null)} style={{
                  flex: 1, padding: '13px', background: '#F5F5F5', color: '#888',
                  border: 'none', borderRadius: '12px', cursor: 'pointer',
                  fontFamily: 'inherit', fontWeight: 800, fontSize: '14px',
                }}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
