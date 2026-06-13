import { useState, useEffect } from 'react'
import axios from 'axios'
import LessonPlanViewer from './LessonPlanViewer'
import BadgeDisplay from './BadgeDisplay'
import SessionHistory from './SessionHistory'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function ParentDashboard({ token, selectedProfileId, onBack }) {
  const [summary, setSummary] = useState(null)
  const [childData, setChildData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  // Lesson plan generation
  const [planForm, setPlanForm] = useState({ subject: 'spelling', grade: 'Grade 1', duration: '1 week', focus_areas: '' })
  const [generatingPlan, setGeneratingPlan] = useState(false)
  const [generatedPlan, setGeneratedPlan] = useState(null)
  const [savedPlans, setSavedPlans] = useState([])
  const [viewingPlan, setViewingPlan] = useState(null)

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
      // Refresh list
      const plansRes = await axios.get(`${API_URL}/lesson-plans/`, { headers })
      setSavedPlans(plansRes.data.lesson_plans || [])
    } catch (e) {
      console.error(e)
    } finally {
      setGeneratingPlan(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: '#888' }}>
      Loading dashboard... 🐦
    </div>
  )

  const tabStyle = (tab) => ({
    padding: '8px 16px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '13px',
    background: activeTab === tab ? '#6EB4D4' : '#f0f0f0',
    color: activeTab === tab ? 'white' : '#555',
  })

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ color: '#CC2929', margin: 0 }}>📊 Parent Dashboard</h2>
          {childData && <p style={{ color: '#888', margin: '4px 0 0', fontSize: '14px' }}>Viewing: {childData.child_name}</p>}
        </div>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#6EB4D4', cursor: 'pointer', fontWeight: 600, fontSize: '14px' }}>
          ← Back to Chat
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
          {[
            { label: 'Total Sessions', value: summary.total_sessions, emoji: '📚' },
            { label: 'Correct Answers', value: summary.total_correct, emoji: '✅' },
            { label: 'Accuracy', value: `${summary.accuracy_percent}%`, emoji: '🎯' },
          ].map(card => (
            <div key={card.label} style={{
              background: 'white', borderRadius: '12px', padding: '16px', textAlign: 'center',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #f0f0f0',
            }}>
              <div style={{ fontSize: '28px' }}>{card.emoji}</div>
              <div style={{ fontSize: '22px', fontWeight: 700, color: '#CC2929' }}>{card.value}</div>
              <div style={{ fontSize: '12px', color: '#888' }}>{card.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Message usage bar */}
      {childData?.message_count && (
        <div style={{ background: 'white', borderRadius: '12px', padding: '14px 16px', marginBottom: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '13px' }}>
            <span style={{ fontWeight: 600, color: '#333' }}>💬 Messages Used</span>
            <span style={{ color: '#666' }}>{childData.message_count.used} / {childData.message_count.limit}</span>
          </div>
          <div style={{ background: '#f0f0f0', borderRadius: '6px', height: '8px', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: '6px', transition: 'width 0.5s',
              background: childData.message_count.used / childData.message_count.limit > 0.8 ? '#CC2929' : '#6EB4D4',
              width: `${Math.min(100, childData.message_count.used / childData.message_count.limit * 100)}%`,
            }} />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {['overview', 'badges', 'lesson-plans', 'history'].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={tabStyle(tab)}>
            {tab === 'overview' ? '📈 Overview' : tab === 'badges' ? '🏅 Badges' : tab === 'lesson-plans' ? '📝 Lesson Plans' : '📖 History'}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && childData && (
        <div style={{ background: 'white', borderRadius: '12px', padding: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <h4 style={{ color: '#4A8B3F', marginBottom: '12px' }}>Progress by Subject</h4>
          {Object.entries(childData.progress_by_subject || {}).map(([subj, data]) => (
            <div key={subj} style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{subj}</span>
                <span style={{ color: '#666' }}>{data.correct}/{data.total} ({data.accuracy_pct}%)</span>
              </div>
              <div style={{ background: '#f0f0f0', borderRadius: '6px', height: '8px' }}>
                <div style={{
                  height: '100%', borderRadius: '6px', background: '#4A8B3F',
                  width: `${data.accuracy_pct}%`,
                }} />
              </div>
            </div>
          ))}
          <p style={{ fontSize: '13px', color: '#888', marginTop: '12px' }}>
            🔥 {childData.streak_days}-day streak
          </p>
        </div>
      )}

      {/* Badges Tab */}
      {activeTab === 'badges' && (
        <div style={{ background: 'white', borderRadius: '12px', padding: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <h4 style={{ color: '#4A8B3F', marginBottom: '12px' }}>Earned Badges</h4>
          {childData?.badges?.length
            ? <BadgeDisplay badges={childData.badges} />
            : <p style={{ color: '#888', fontSize: '14px' }}>No badges yet — keep learning to earn them! 🌟</p>
          }
        </div>
      )}

      {/* Lesson Plans Tab */}
      {activeTab === 'lesson-plans' && (
        <div>
          {/* Generate form */}
          <div style={{ background: 'white', borderRadius: '12px', padding: '16px', marginBottom: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
            <h4 style={{ color: '#4A8B3F', marginBottom: '12px' }}>🪺 Generate Lesson Plan</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
              <select value={planForm.subject} onChange={e => setPlanForm(p => ({ ...p, subject: e.target.value }))}
                style={{ padding: '8px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }}>
                {['spelling', 'math', 'rhyming', 'grammar', 'puzzles', 'literature'].map(s => (
                  <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
              <input placeholder="Grade (e.g. Grade 1)" value={planForm.grade}
                onChange={e => setPlanForm(p => ({ ...p, grade: e.target.value }))}
                style={{ padding: '8px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
              <input placeholder="Duration (e.g. 1 week)" value={planForm.duration}
                onChange={e => setPlanForm(p => ({ ...p, duration: e.target.value }))}
                style={{ padding: '8px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
              <input placeholder="Focus areas (optional)" value={planForm.focus_areas}
                onChange={e => setPlanForm(p => ({ ...p, focus_areas: e.target.value }))}
                style={{ padding: '8px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
            </div>
            <button onClick={generatePlan} disabled={generatingPlan}
              style={{
                padding: '10px 20px', background: '#CC2929', color: 'white', border: 'none',
                borderRadius: '8px', cursor: generatingPlan ? 'not-allowed' : 'pointer', fontWeight: 600,
                opacity: generatingPlan ? 0.7 : 1,
              }}>
              {generatingPlan ? '🪺 Mama Bird is preparing...' : '✨ Generate Plan'}
            </button>
          </div>

          {generatedPlan && (
            <div style={{ background: 'white', borderRadius: '12px', padding: '16px', marginBottom: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
              <LessonPlanViewer plan={generatedPlan} />
            </div>
          )}

          {savedPlans.length > 0 && (
            <div style={{ background: 'white', borderRadius: '12px', padding: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
              <h4 style={{ color: '#4A8B3F', marginBottom: '12px' }}>Saved Plans</h4>
              {savedPlans.map(p => (
                <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <span style={{ fontSize: '13px', color: '#333' }}>{p.title || `${p.subject} - ${p.grade}`}</span>
                  <button onClick={() => setViewingPlan(viewingPlan === p.id ? null : p.id)}
                    style={{ background: 'none', border: '1px solid #6EB4D4', color: '#6EB4D4', borderRadius: '6px', padding: '4px 10px', cursor: 'pointer', fontSize: '12px' }}>
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
        <div style={{ background: 'white', borderRadius: '12px', padding: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <SessionHistory token={token} childProfileId={selectedProfileId} />
        </div>
      )}
    </div>
  )
}
