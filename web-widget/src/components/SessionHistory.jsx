import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function SessionHistory({ token, childProfileId }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [expandedData, setExpandedData] = useState({})
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    if (!childProfileId) return
    setLoading(true)
    axios.get(`${API_URL}/sessions/${childProfileId}?page=${page}&limit=15`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => {
      setSessions(res.data.sessions || [])
      setTotal(res.data.total || 0)
    }).catch(console.error)
      .finally(() => setLoading(false))
  }, [childProfileId, page, token])

  const loadSession = async (sessionId) => {
    if (expandedData[sessionId]) {
      setExpanded(expanded === sessionId ? null : sessionId)
      return
    }
    try {
      const res = await axios.get(`${API_URL}/sessions/${childProfileId}/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setExpandedData(prev => ({ ...prev, [sessionId]: res.data }))
      setExpanded(sessionId)
    } catch (e) { console.error(e) }
  }

  const charEmoji = (char) => char === 'character_1' ? '🐦' : '🪺'

  if (loading) return <div style={{ padding: '20px', textAlign: 'center', color: '#888' }}>Loading sessions...</div>
  if (!sessions.length) return <div style={{ padding: '20px', textAlign: 'center', color: '#888' }}>No sessions yet. Start chatting! 🐦</div>

  return (
    <div>
      <h3 style={{ color: '#CC2929', marginBottom: '12px' }}>Session History ({total} total)</h3>
      {sessions.map(s => (
        <div key={s.id} style={{ marginBottom: '8px', border: '1px solid #e0e0e0', borderRadius: '10px', overflow: 'hidden' }}>
          <button
            onClick={() => loadSession(s.id)}
            style={{
              width: '100%', textAlign: 'left', padding: '10px 14px',
              background: expanded === s.id ? '#6EB4D4' : '#f9f9f9',
              color: expanded === s.id ? 'white' : '#333',
              border: 'none', cursor: 'pointer', fontSize: '13px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}
          >
            <span>{charEmoji(s.character)} {s.subject} — {new Date(s.created_at).toLocaleDateString()}</span>
            <span style={{ fontSize: '11px', opacity: 0.8 }}>{s.message_count} msg {expanded === s.id ? '▲' : '▼'}</span>
          </button>

          {expanded === s.id && expandedData[s.id] && (
            <div style={{ padding: '10px 14px', background: 'white' }}>
              {(expandedData[s.id].messages || []).map((msg, i) => (
                <div key={i} style={{
                  marginBottom: '6px', padding: '6px 10px', borderRadius: '8px',
                  background: msg.role === 'user' ? '#E3F2FD' : '#F1F8E9',
                  fontSize: '13px', color: '#333',
                }}>
                  <strong style={{ fontSize: '11px', color: '#888' }}>
                    {msg.role === 'user' ? '👤 You' : `${charEmoji(s.character)} AI`}:
                  </strong>{' '}
                  {msg.content}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {total > 15 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '12px' }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            style={{ padding: '6px 14px', borderRadius: '8px', border: '1px solid #ccc', cursor: 'pointer', background: 'white' }}>
            ← Prev
          </button>
          <span style={{ padding: '6px', color: '#666', fontSize: '13px' }}>Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * 15 >= total}
            style={{ padding: '6px 14px', borderRadius: '8px', border: '1px solid #ccc', cursor: 'pointer', background: 'white' }}>
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
