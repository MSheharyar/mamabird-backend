import { useState } from 'react'

export default function LessonPlanViewer({ plan }) {
  const [openDay, setOpenDay] = useState(null)

  if (!plan) return null

  // Fallback: if Claude returned raw text instead of structured JSON
  if (plan.raw_content) {
    return (
      <div style={{ fontFamily: 'inherit' }}>
        <h3 style={{ color: '#CC2929', marginBottom: '10px', fontWeight: 800 }}>Lesson Plan</h3>
        <pre style={{
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontSize: '13px', color: '#444', lineHeight: 1.7,
          background: '#FAFAFA', borderRadius: '10px', padding: '14px',
          border: '1px solid #E8E8E8',
        }}>
          {plan.raw_content}
        </pre>
      </div>
    )
  }

  const days = plan.days || []
  const tips = Array.isArray(plan.parent_tips)
    ? plan.parent_tips.join(' · ')
    : plan.parent_tips

  return (
    <div style={{ fontFamily: 'inherit' }}>
      <h3 style={{ color: '#CC2929', marginBottom: '6px', fontWeight: 800 }}>
        {plan.title || 'Lesson Plan'}
      </h3>
      {plan.overview && (
        <p style={{ color: '#555', fontSize: '14px', marginBottom: '14px', lineHeight: 1.6 }}>{plan.overview}</p>
      )}

      {plan.objectives && plan.objectives.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <strong style={{ color: '#4A8B3F', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Learning Objectives
          </strong>
          <ul style={{ margin: '8px 0 0 18px', padding: 0, fontSize: '13px', color: '#444', lineHeight: 1.7 }}>
            {plan.objectives.map((obj, i) => <li key={i}>{obj}</li>)}
          </ul>
        </div>
      )}

      {days.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          {days.map((day, i) => (
            <div key={i} style={{ marginBottom: '6px', border: '1px solid #E8E8E8', borderRadius: '12px', overflow: 'hidden' }}>
              <button
                onClick={() => setOpenDay(openDay === i ? null : i)}
                style={{
                  width: '100%', textAlign: 'left', padding: '11px 16px',
                  background: openDay === i ? 'linear-gradient(135deg, #6EB4D4, #4A96BC)' : '#F8F8F8',
                  color: openDay === i ? 'white' : '#333',
                  border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '13px',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  fontFamily: 'inherit', transition: 'all 0.18s',
                }}
              >
                <span>{day.day ? `Day ${day.day}` : `Day ${i + 1}`}{day.title ? ` — ${day.title}` : ''}</span>
                <span style={{ fontSize: '11px', opacity: 0.7 }}>{openDay === i ? '▲' : '▼'}</span>
              </button>

              {openDay === i && (
                <div style={{ padding: '14px 16px', fontSize: '13px', color: '#444', background: 'white', lineHeight: 1.7 }}>
                  {day.objective && <p style={{ marginBottom: '8px' }}><strong style={{ color: '#4A8B3F' }}>Objective:</strong> {day.objective}</p>}
                  {day.warmup && <p style={{ marginBottom: '8px' }}><strong style={{ color: '#6EB4D4' }}>Warm-up:</strong> {day.warmup}</p>}
                  {day.main_activity && <p style={{ marginBottom: '8px' }}><strong style={{ color: '#CC2929' }}>Main Activity:</strong> {day.main_activity}</p>}
                  {day.practice && <p style={{ marginBottom: '8px' }}><strong>Practice:</strong> {day.practice}</p>}
                  {day.assessment && <p style={{ marginBottom: '8px' }}><strong>Assessment:</strong> {day.assessment}</p>}
                  {day.homework && <p style={{ marginBottom: '0' }}><strong>Homework:</strong> {day.homework}</p>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {plan.materials_needed && plan.materials_needed.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <strong style={{ color: '#4A8B3F', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Materials Needed
          </strong>
          <ul style={{ margin: '8px 0 0 18px', padding: 0, fontSize: '13px', color: '#444', lineHeight: 1.7 }}>
            {plan.materials_needed.map((m, i) => <li key={i}>{m}</li>)}
          </ul>
        </div>
      )}

      {tips && (
        <div style={{ marginTop: '12px', background: '#FFF9C4', borderRadius: '10px', padding: '12px 14px', border: '1px solid rgba(245,194,0,0.3)' }}>
          <strong style={{ color: '#B8860B', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Parent Tips
          </strong>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: '#555', lineHeight: 1.6 }}>{tips}</p>
        </div>
      )}
    </div>
  )
}
