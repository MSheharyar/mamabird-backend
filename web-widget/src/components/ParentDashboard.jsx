import { useState, useEffect } from 'react'
import axios from 'axios'
import LessonPlanViewer from './LessonPlanViewer'
import BadgeDisplay from './BadgeDisplay'
import SessionHistory from './SessionHistory'
import Icon from './Icon'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STAT_CARDS = [
  { key: 'total_sessions',   label: 'Total Sessions',  icon: 'bar-chart',   color: '#6EB4D4', bg: '#EBF6FC' },
  { key: 'total_correct',    label: 'Correct Answers', icon: 'check-circle', color: '#4A8B3F', bg: '#E8F5E4' },
  { key: 'accuracy_percent', label: 'Accuracy',        icon: 'target',       color: '#CC2929', bg: '#FFF0F0', suffix: '%' },
]

const TABS = [
  { id: 'overview',     label: 'Overview',      icon: 'trending-up' },
  { id: 'badges',       label: 'Badges',        icon: 'award' },
  { id: 'lesson-plans', label: 'Lesson Plans',  icon: 'book-open' },
  { id: 'history',      label: 'History',       icon: 'clock' },
]

export default function ParentDashboard({ token, selectedProfileId, onBack }) {
  const [summary, setSummary] = useState(null)
  const [childData, setChildData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [planForm, setPlanForm] = useState({ subject: 'spelling', grade: 'Grade 1', duration: '1 week', focus_areas: '' })
  const [generatingPlan, setGeneratingPlan] = useState(false)
  const [generatedPlan, setGeneratedPlan] = useState(null)
  const [savedPlans, setSavedPlans] = useState([])
  const [viewingPlan, setViewingPlan] = useState(null)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [sumRes, plansRes] = await Promise.all([
          axios.get(`${API_URL}/dashboard/summary`, { headers }),
          axios.get(`${API_URL}/lesson-plans/`, { headers }),
        ])
        setSummary(sumRes.data)
        setSavedPlans(plansRes.data.lesson_plans || [])
        if (selectedProfileId) {
          const childRes = await axios.get(`${API_URL}/dashboard/child/${selectedProfileId}`, { headers })
          setChildData(childRes.data)
        }
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    load()
  }, [token, selectedProfileId])

  const generatePlan = async () => {
    setGeneratingPlan(true)
    setGeneratedPlan(null)
    try {
      const res = await axios.post(`${API_URL}/lesson-plans/generate`, {
        ...planForm,
        child_profile_id: selectedProfileId || undefined,
      }, { headers })
      setGeneratedPlan(res.data.plan)
      const plansRes = await axios.get(`${API_URL}/lesson-plans/`, { headers })
      setSavedPlans(plansRes.data.lesson_plans || [])
    } catch (e) { console.error(e) }
    finally { setGeneratingPlan(false) }
  }

  const downloadPdf = async () => {
    if (!selectedProfileId) return
    setDownloadingPdf(true)
    try {
      const res = await axios.get(
        `${API_URL}/dashboard/child/${selectedProfileId}/export-pdf`,
        { headers, responseType: 'blob' }
      )
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `progress_report_${childData?.child_name || 'child'}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) { console.error('PDF download failed', e) }
    finally { setDownloadingPdf(false) }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column', gap: '12px' }}>
        <div style={{ fontSize: '48px', animation: 'float 2s ease-in-out infinite' }}>🐦</div>
        <div style={{ color: '#888', fontSize: '14px', fontWeight: 700 }}>Loading dashboard...</div>
      </div>
    )
  }

  const usedPct = childData?.message_count
    ? Math.min(100, childData.message_count.used / childData.message_count.limit * 100)
    : 0
  const barColor = usedPct > 80 ? '#CC2929' : usedPct > 55 ? '#F5C200' : '#4A8B3F'

  return (
    <div style={{ padding: '24px', maxWidth: '820px', margin: '0 auto', fontFamily: 'inherit' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '12px' }}>
        <div>
          <h2 style={{
            color: '#CC2929', margin: 0, fontSize: '22px', fontWeight: 800,
            display: 'flex', alignItems: 'center', gap: '8px',
          }}>
            <Icon name="bar-chart" size={22} color="#CC2929" />
            Parent Dashboard
          </h2>
          {childData && (
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              marginTop: '6px', padding: '3px 12px',
              background: 'linear-gradient(135deg, #EBF6FC, #D6EEFB)',
              borderRadius: '20px', fontSize: '12px', fontWeight: 800,
              color: '#4A96BC', border: '1px solid rgba(110,180,212,0.3)',
            }}>
              <Icon name="user" size={12} color="#4A96BC" />
              {childData.child_name}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {selectedProfileId && (
            <button
              onClick={downloadPdf}
              disabled={downloadingPdf}
              style={{
                padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px',
                background: downloadingPdf ? '#ccc' : 'linear-gradient(135deg, #4A8B3F, #3A7030)',
                color: 'white', border: 'none', borderRadius: '10px',
                cursor: downloadingPdf ? 'not-allowed' : 'pointer',
                fontFamily: 'inherit', fontWeight: 800, fontSize: '13px',
                boxShadow: '0 3px 10px rgba(74,139,63,0.3)', transition: 'all 0.18s',
              }}
            >
              <Icon name="download" size={14} color="white" />
              {downloadingPdf ? 'Generating...' : 'Download PDF'}
            </button>
          )}
          <button onClick={onBack} style={{
            background: 'none', border: '2px solid #E8E8E8', color: '#6EB4D4',
            cursor: 'pointer', fontWeight: 800, fontSize: '13px',
            borderRadius: '10px', padding: '7px 12px', fontFamily: 'inherit',
            display: 'flex', alignItems: 'center', gap: '5px', transition: 'all 0.15s',
          }}>
            <Icon name="arrow-left" size={13} color="#6EB4D4" />
            Back
          </button>
        </div>
      </div>

      {/* Stat Cards */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginBottom: '16px' }}>
          {STAT_CARDS.map(card => (
            <div key={card.key} style={{
              background: 'white', borderRadius: '16px', padding: '18px 16px',
              textAlign: 'center', boxShadow: '0 3px 12px rgba(0,0,0,0.07)',
              border: '1px solid #F0F0F0', borderTop: `4px solid ${card.color}`,
            }}>
              <div style={{
                width: '44px', height: '44px', borderRadius: '12px',
                background: card.bg, display: 'flex', alignItems: 'center',
                justifyContent: 'center', margin: '0 auto 10px',
              }}>
                <Icon name={card.icon} size={22} color={card.color} />
              </div>
              <div style={{ fontSize: '26px', fontWeight: 800, color: card.color }}>
                {summary[card.key]}{card.suffix || ''}
              </div>
              <div style={{ fontSize: '11px', color: '#999', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', marginTop: '3px' }}>
                {card.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Message Usage Bar */}
      {childData?.message_count && (
        <div style={{
          background: 'white', borderRadius: '14px', padding: '14px 18px',
          marginBottom: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #F0F0F0',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontWeight: 800, color: '#333', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Icon name="message" size={14} color="#888" />
              Messages Used
            </span>
            <span style={{ color: '#888', fontSize: '13px', fontWeight: 700 }}>
              {childData.message_count.used} / {childData.message_count.limit}
            </span>
          </div>
          <div style={{ background: '#F0F0F0', borderRadius: '8px', height: '9px', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: '8px',
              background: `linear-gradient(90deg, ${barColor}, ${barColor}CC)`,
              width: `${usedPct}%`, transition: 'width 0.6s ease',
            }} />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '18px', flexWrap: 'wrap' }}>
        {TABS.map(tab => {
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 16px', border: 'none', borderRadius: '20px',
                cursor: 'pointer', fontFamily: 'inherit', fontWeight: 800, fontSize: '13px',
                display: 'flex', alignItems: 'center', gap: '6px',
                transition: 'all 0.18s',
                background: active ? 'linear-gradient(135deg, #6EB4D4, #4A96BC)' : '#F0F0F0',
                color: active ? 'white' : '#666',
                boxShadow: active ? '0 3px 10px rgba(110,180,212,0.4)' : 'none',
                transform: active ? 'translateY(-1px)' : 'none',
              }}
            >
              <Icon name={tab.icon} size={14} color={active ? 'white' : '#888'} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div style={{
          background: 'white', borderRadius: '16px', padding: '20px',
          boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0',
        }}>
          <h4 style={{
            color: '#4A8B3F', marginBottom: '16px', fontSize: '13px',
            textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: 800,
            display: 'flex', alignItems: 'center', gap: '7px',
          }}>
            <Icon name="trending-up" size={15} color="#4A8B3F" />
            Progress by Subject
          </h4>
          {!childData && (
            <div style={{ color: '#bbb', fontSize: '14px', fontWeight: 600, textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: '36px', marginBottom: '8px' }}>🐦</div>
              No child profile selected — go back and pick a profile to see progress.
            </div>
          )}
          {childData && Object.keys(childData.progress_by_subject || {}).length === 0 && (
            <p style={{ color: '#bbb', fontSize: '14px', fontWeight: 600 }}>No subject data yet — start chatting!</p>
          )}
          {childData && Object.entries(childData.progress_by_subject || {}).map(([subj, data]) => (
            <div key={subj} style={{ marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '5px' }}>
                <span style={{ textTransform: 'capitalize', fontWeight: 800, color: '#333' }}>{subj}</span>
                <span style={{
                  fontWeight: 800,
                  color: data.accuracy_pct >= 80 ? '#4A8B3F' : data.accuracy_pct >= 50 ? '#B8860B' : '#CC2929',
                }}>
                  {data.correct}/{data.total} · {data.accuracy_pct}%
                </span>
              </div>
              <div style={{ background: '#F0F0F0', borderRadius: '8px', height: '9px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: '8px', transition: 'width 0.6s ease',
                  background: data.accuracy_pct >= 80
                    ? 'linear-gradient(90deg, #4A8B3F, #5EA852)'
                    : data.accuracy_pct >= 50
                    ? 'linear-gradient(90deg, #F5C200, #E6B300)'
                    : 'linear-gradient(90deg, #CC2929, #E03D3D)',
                  width: `${data.accuracy_pct}%`,
                }} />
              </div>
            </div>
          ))}
          {childData?.streak_days > 0 && (
            <div style={{
              marginTop: '16px', display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '6px 14px', background: 'linear-gradient(135deg, #FFF8E1, #FFF3C0)',
              borderRadius: '20px', fontSize: '13px', fontWeight: 800, color: '#7A5C00',
              border: '1px solid rgba(245,194,0,0.4)',
            }}>
              <Icon name="flame" size={14} color="#E87000" />
              {childData.streak_days}-day streak!
            </div>
          )}
        </div>
      )}

      {/* Badges Tab */}
      {activeTab === 'badges' && (
        <div style={{
          background: 'white', borderRadius: '16px', padding: '20px',
          boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0',
        }}>
          <h4 style={{
            color: '#4A8B3F', marginBottom: '14px', fontWeight: 800, fontSize: '13px',
            textTransform: 'uppercase', letterSpacing: '0.6px',
            display: 'flex', alignItems: 'center', gap: '7px',
          }}>
            <Icon name="award" size={15} color="#4A8B3F" />
            Earned Badges
          </h4>
          {childData?.badges?.length
            ? <BadgeDisplay badges={childData.badges} />
            : <p style={{ color: '#bbb', fontSize: '14px', fontWeight: 600 }}>No badges yet — keep learning to earn them!</p>
          }
        </div>
      )}

      {/* Lesson Plans Tab */}
      {activeTab === 'lesson-plans' && (
        <div>
          <div style={{
            background: 'white', borderRadius: '16px', padding: '20px',
            marginBottom: '16px', boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0',
          }}>
            <h4 style={{
              color: '#4A8B3F', marginBottom: '14px', fontWeight: 800, fontSize: '13px',
              textTransform: 'uppercase', letterSpacing: '0.6px',
              display: 'flex', alignItems: 'center', gap: '7px',
            }}>
              <Icon name="edit" size={15} color="#4A8B3F" />
              Generate Lesson Plan
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
              {[
                { key: 'subject', type: 'select', options: ['spelling','math','rhyming','grammar','puzzles','literature'], label: 'Subject' },
                { key: 'grade', type: 'text', placeholder: 'Grade (e.g. Grade 1)', label: 'Grade' },
                { key: 'duration', type: 'text', placeholder: 'Duration (e.g. 1 week)', label: 'Duration' },
                { key: 'focus_areas', type: 'text', placeholder: 'Focus areas (optional)', label: 'Focus Areas' },
              ].map(field => (
                <div key={field.key}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 800, color: '#888', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    {field.label}
                  </label>
                  {field.type === 'select' ? (
                    <select
                      value={planForm[field.key]}
                      onChange={e => setPlanForm(p => ({ ...p, [field.key]: e.target.value }))}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '10px', border: '2px solid #E8E8E8', fontFamily: 'inherit', fontSize: '13px', fontWeight: 700, background: '#FAFAFA', outline: 'none' }}
                    >
                      {field.options.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                    </select>
                  ) : (
                    <input
                      placeholder={field.placeholder}
                      value={planForm[field.key]}
                      onChange={e => setPlanForm(p => ({ ...p, [field.key]: e.target.value }))}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '10px', border: '2px solid #E8E8E8', fontFamily: 'inherit', fontSize: '13px', fontWeight: 700, background: '#FAFAFA', outline: 'none' }}
                    />
                  )}
                </div>
              ))}
            </div>
            <button
              onClick={generatePlan}
              disabled={generatingPlan}
              style={{
                padding: '11px 20px', display: 'flex', alignItems: 'center', gap: '7px',
                background: generatingPlan ? '#ccc' : 'linear-gradient(135deg, #CC2929, #A82020)',
                color: 'white', border: 'none', borderRadius: '10px',
                cursor: generatingPlan ? 'not-allowed' : 'pointer',
                fontFamily: 'inherit', fontWeight: 800, fontSize: '14px',
                boxShadow: generatingPlan ? 'none' : '0 3px 12px rgba(204,41,41,0.3)',
                transition: 'all 0.18s',
              }}
            >
              <Icon name="zap" size={15} color="white" />
              {generatingPlan ? 'Mama Bird is preparing...' : 'Generate Plan'}
            </button>
          </div>

          {generatedPlan && (
            <div style={{ background: 'white', borderRadius: '16px', padding: '20px', marginBottom: '16px', boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0' }}>
              <LessonPlanViewer plan={generatedPlan} />
            </div>
          )}

          {savedPlans.length > 0 && (
            <div style={{ background: 'white', borderRadius: '16px', padding: '20px', boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0' }}>
              <h4 style={{
                color: '#4A8B3F', marginBottom: '14px', fontWeight: 800, fontSize: '13px',
                textTransform: 'uppercase', letterSpacing: '0.6px',
                display: 'flex', alignItems: 'center', gap: '7px',
              }}>
                <Icon name="file" size={14} color="#4A8B3F" />
                Saved Plans
              </h4>
              {savedPlans.map(p => (
                <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #F5F5F5' }}>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#333' }}>{p.title || `${p.subject} — ${p.grade}`}</span>
                  <button
                    onClick={() => setViewingPlan(viewingPlan === p.id ? null : p.id)}
                    style={{
                      background: 'none', border: '2px solid #6EB4D4', color: '#6EB4D4',
                      borderRadius: '8px', padding: '4px 12px', cursor: 'pointer',
                      fontSize: '12px', fontFamily: 'inherit', fontWeight: 800, transition: 'all 0.15s',
                    }}
                  >
                    {viewingPlan === p.id ? 'Hide' : 'View'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && selectedProfileId && (
        <div style={{ background: 'white', borderRadius: '16px', padding: '20px', boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0' }}>
          <SessionHistory token={token} childProfileId={selectedProfileId} />
        </div>
      )}
      {activeTab === 'history' && !selectedProfileId && (
        <div style={{ background: 'white', borderRadius: '16px', padding: '24px 20px', textAlign: 'center', boxShadow: '0 3px 12px rgba(0,0,0,0.07)', border: '1px solid #F0F0F0', color: '#bbb', fontWeight: 600, fontSize: '14px' }}>
          Select a child profile to view session history.
        </div>
      )}
    </div>
  )
}
