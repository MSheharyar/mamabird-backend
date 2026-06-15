import { useState, useEffect } from 'react'
import axios from 'axios'
import Icon from './Icon'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATUS_COLORS = {
  active:       { bg: '#E8F5E4', color: '#3A7030', border: '#4A8B3F' },
  trial:        { bg: '#EBF6FC', color: '#4A96BC', border: '#6EB4D4' },
  grace_period: { bg: '#FFFBEA', color: '#7A5C00', border: '#F5C200' },
  cancelled:    { bg: '#FFF0F0', color: '#A82020', border: '#CC2929' },
}

const STAT_CONFIG = [
  { key: 'total_users',         label: 'Total Users',         icon: 'users',       color: '#6EB4D4', bg: '#EBF6FC' },
  { key: 'active_subscribers',  label: 'Active Subscribers',  icon: 'check-circle', color: '#4A8B3F', bg: '#E8F5E4' },
  { key: 'trial_users',         label: 'Trial Users',         icon: 'clock',        color: '#F5C200', bg: '#FFFBEA' },
  { key: 'api_cost_this_month', label: 'API Cost This Month', icon: 'activity',     color: '#CC2929', bg: '#FFF0F0', prefix: '$', decimals: 4 },
]

const card = {
  background: 'white', borderRadius: '16px',
  boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0',
}

export default function AdminPanel({ token, onBack }) {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [usage, setUsage] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [extendModal, setExtendModal] = useState(null)
  const [extendDays, setExtendDays] = useState(7)
  const [actionMsg, setActionMsg] = useState('')
  const [actionOk, setActionOk] = useState(true)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      const [statsRes, usersRes, usageRes] = await Promise.all([
        axios.get(`${API_URL}/admin/stats`, { headers }),
        axios.get(`${API_URL}/admin/users`, { headers }),
        axios.get(`${API_URL}/admin/usage`, { headers }),
      ])
      setStats(statsRes.data)
      setUsers(usersRes.data.users || [])
      setUsage(usageRes.data.daily || [])
    } catch (e) { console.error('Admin load error', e) }
    finally { setLoading(false) }
  }

  const doExtendTrial = async () => {
    if (!extendModal) return
    try {
      await axios.put(`${API_URL}/admin/users/${extendModal.userId}/extend-trial`, { days: extendDays }, { headers })
      setActionMsg(`Trial extended by ${extendDays} days for ${extendModal.email}`)
      setActionOk(true)
      setExtendModal(null)
      loadAll()
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
      loadAll()
    } catch (e) {
      setActionMsg(e.response?.data?.detail || 'Failed to cancel')
      setActionOk(false)
    }
  }

  const filteredUsers = filter === 'all' ? users : users.filter(u => u.subscription_status === filter)
  const maxCost = Math.max(...usage.map(d => d.cost_usd), 0.001)

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column', gap: '12px' }}>
        <div style={{ animation: 'float 2s ease-in-out infinite' }}>
          <Icon name="shield" size={48} color="#CC2929" />
        </div>
        <div style={{ color: '#888', fontSize: '14px', fontWeight: 700 }}>Loading admin panel...</div>
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', maxWidth: '960px', margin: '0 auto', fontFamily: 'inherit' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ color: '#CC2929', margin: 0, fontSize: '22px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="shield" size={22} color="#CC2929" />
            Admin Panel
          </h2>
          <p style={{ color: '#999', margin: '4px 0 0', fontSize: '13px', fontWeight: 600 }}>MamaBird & Chirpy — Client Management</p>
        </div>
        <button onClick={onBack} style={{
          background: 'none', border: '2px solid #E8E8E8', color: '#6EB4D4',
          cursor: 'pointer', fontWeight: 800, fontSize: '13px',
          borderRadius: '10px', padding: '7px 12px', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', gap: '5px', transition: 'all 0.15s',
        }}>
          <Icon name="arrow-left" size={13} color="#6EB4D4" />
          Back to Chat
        </button>
      </div>

      {/* Action message */}
      {actionMsg && (
        <div style={{
          background: actionOk ? '#E8F5E4' : '#FFF0F0',
          color: actionOk ? '#3A7030' : '#A82020',
          padding: '11px 16px', borderRadius: '10px', marginBottom: '18px',
          fontSize: '13px', fontWeight: 700,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          border: `1px solid ${actionOk ? '#4A8B3F' : '#CC2929'}22`,
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
            <Icon name={actionOk ? 'check' : 'alert'} size={14} color={actionOk ? '#3A7030' : '#A82020'} />
            {actionMsg}
          </span>
          <button onClick={() => setActionMsg('')} style={{ background: 'none', border: 'none', cursor: 'pointer', lineHeight: 1, color: 'inherit', padding: '0 4px' }}>
            <Icon name="x" size={16} color="inherit" />
          </button>
        </div>
      )}

      {/* Stats Row */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
          {STAT_CONFIG.map(s => (
            <div key={s.key} style={{ ...card, padding: '18px 16px', borderLeft: `4px solid ${s.color}`, textAlign: 'center' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 10px' }}>
                <Icon name={s.icon} size={20} color={s.color} />
              </div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: s.color }}>
                {s.prefix || ''}{typeof stats[s.key] === 'number' && s.decimals ? stats[s.key].toFixed(s.decimals) : stats[s.key]}
              </div>
              <div style={{ fontSize: '10px', color: '#aaa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', marginTop: '3px' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Usage Chart */}
      {usage.length > 0 && (
        <div style={{ ...card, padding: '20px', marginBottom: '20px' }}>
          <h4 style={{
            color: '#4A8B3F', margin: '0 0 16px', fontWeight: 800, fontSize: '13px',
            textTransform: 'uppercase', letterSpacing: '0.6px',
            display: 'flex', alignItems: 'center', gap: '7px',
          }}>
            <Icon name="trending-up" size={15} color="#4A8B3F" />
            API Usage — Last 30 Days
          </h4>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '90px', overflowX: 'auto', paddingBottom: '4px' }}>
            {usage.map(day => (
              <div key={day.date} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '18px' }}>
                <div
                  title={`${day.date}: ${day.messages} msgs · $${day.cost_usd.toFixed(4)}`}
                  style={{
                    width: '14px',
                    height: `${Math.max(4, (day.cost_usd / maxCost) * 75)}px`,
                    background: 'linear-gradient(180deg, #6EB4D4, #4A96BC)',
                    borderRadius: '4px 4px 0 0',
                    cursor: 'default', transition: 'opacity 0.15s',
                  }}
                />
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#ccc', marginTop: '6px', fontWeight: 700 }}>
            <span>{usage[0]?.date}</span>
            <span>{usage[usage.length - 1]?.date}</span>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div style={{ ...card, padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <h4 style={{
            color: '#4A8B3F', margin: 0, fontWeight: 800, fontSize: '13px',
            textTransform: 'uppercase', letterSpacing: '0.6px',
            display: 'flex', alignItems: 'center', gap: '7px',
          }}>
            <Icon name="users" size={15} color="#4A8B3F" />
            Users ({filteredUsers.length})
          </h4>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {['all', 'trial', 'active', 'grace_period', 'cancelled'].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: '5px 12px', border: 'none', borderRadius: '20px', cursor: 'pointer',
                fontSize: '11px', fontWeight: 800, fontFamily: 'inherit', transition: 'all 0.15s',
                background: filter === f ? 'linear-gradient(135deg, #CC2929, #A82020)' : '#F0F0F0',
                color: filter === f ? 'white' : '#666',
                boxShadow: filter === f ? '0 2px 8px rgba(204,41,41,0.3)' : 'none',
              }}>
                {f === 'all' ? 'All' : f === 'grace_period' ? 'Grace' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                {['Email', 'Plan', 'Status', 'Children', 'Joined', 'Actions'].map(h => (
                  <th key={h} style={{
                    padding: '10px 12px', textAlign: 'left', color: '#999',
                    fontWeight: 800, fontSize: '11px', borderBottom: '2px solid #F0F0F0',
                    textTransform: 'uppercase', letterSpacing: '0.4px',
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user, i) => {
                const sc = STATUS_COLORS[user.subscription_status] || { bg: '#F5F5F5', color: '#888', border: '#ddd' }
                const joined = user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'
                return (
                  <tr
                    key={user.id}
                    style={{ borderBottom: '1px solid #F8F8F8', background: i % 2 === 1 ? '#FAFAFA' : 'white', transition: 'background 0.12s' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F0F8FF'}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 1 ? '#FAFAFA' : 'white'}
                  >
                    <td style={{ padding: '10px 12px', fontWeight: 700, color: '#333' }}>{user.email}</td>
                    <td style={{ padding: '10px 12px', color: '#888', fontWeight: 600 }}>{user.subscription_plan || '—'}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        background: sc.bg, color: sc.color,
                        border: `1px solid ${sc.border}44`,
                        padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800,
                      }}>
                        {user.subscription_status || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: '#888', fontWeight: 700, textAlign: 'center' }}>{user.child_count}</td>
                    <td style={{ padding: '10px 12px', color: '#bbb', fontSize: '12px', fontWeight: 600 }}>{joined}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          onClick={() => { setExtendModal({ userId: user.id, email: user.email }); setExtendDays(7) }}
                          style={{
                            padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '4px',
                            background: 'linear-gradient(135deg, #6EB4D4, #4A96BC)',
                            color: 'white', border: 'none', borderRadius: '7px',
                            cursor: 'pointer', fontSize: '11px', fontWeight: 800, fontFamily: 'inherit',
                            boxShadow: '0 2px 6px rgba(110,180,212,0.3)', transition: 'all 0.15s',
                          }}
                        >
                          <Icon name="refresh" size={11} color="white" />
                          Extend
                        </button>
                        <button
                          onClick={() => doCancel(user.id, user.email)}
                          style={{
                            padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '4px',
                            background: 'white', color: '#CC2929',
                            border: '1.5px solid #CC2929', borderRadius: '7px',
                            cursor: 'pointer', fontSize: '11px', fontWeight: 800, fontFamily: 'inherit', transition: 'all 0.15s',
                          }}
                        >
                          <Icon name="ban" size={11} color="#CC2929" />
                          Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filteredUsers.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: '28px', textAlign: 'center', color: '#ccc', fontSize: '14px', fontWeight: 700 }}>
                    No users match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Extend Trial Modal */}
      {extendModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000,
          backdropFilter: 'blur(3px)',
        }}>
          <div style={{
            background: 'white', borderRadius: '20px', overflow: 'hidden',
            width: '360px', boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
            animation: 'fadeSlideIn 0.2s ease',
          }}>
            <div style={{ background: 'linear-gradient(135deg, #6EB4D4, #4A96BC)', padding: '18px 24px' }}>
              <h3 style={{ color: 'white', margin: 0, fontWeight: 800, fontSize: '17px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Icon name="refresh" size={17} color="white" />
                Extend Trial
              </h3>
              <p style={{ color: 'rgba(255,255,255,0.85)', margin: '4px 0 0', fontSize: '13px', fontWeight: 600 }}>
                {extendModal.email}
              </p>
            </div>
            <div style={{ padding: '24px' }}>
              <label style={{ fontSize: '12px', fontWeight: 800, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Days to add (1–30)
              </label>
              <input
                type="number" min={1} max={30} value={extendDays}
                onChange={e => setExtendDays(Math.min(30, Math.max(1, Number(e.target.value))))}
                style={{
                  display: 'block', width: '100%', margin: '8px 0 20px',
                  padding: '11px 14px', borderRadius: '10px', border: '2px solid #E8E8E8',
                  fontFamily: 'inherit', fontSize: '18px', fontWeight: 800,
                  outline: 'none', color: '#333',
                }}
              />
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={doExtendTrial} style={{
                  flex: 1, padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px',
                  background: 'linear-gradient(135deg, #4A8B3F, #3A7030)',
                  color: 'white', border: 'none', borderRadius: '10px',
                  cursor: 'pointer', fontFamily: 'inherit', fontWeight: 800, fontSize: '14px',
                  boxShadow: '0 3px 10px rgba(74,139,63,0.3)',
                }}>
                  <Icon name="check" size={15} color="white" />
                  Confirm
                </button>
                <button onClick={() => setExtendModal(null)} style={{
                  flex: 1, padding: '12px', background: '#F5F5F5', color: '#888',
                  border: 'none', borderRadius: '10px', cursor: 'pointer',
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
