import { useState } from 'react'

export default function LessonPlanViewer({ plan }) {
  const [openDay, setOpenDay] = useState(null)

  if (!plan) return null

  const days = plan.days || []

  return (
    <div style={{ fontFamily: 'inherit' }}>
      <h3 style={{ color: '#CC2929', marginBottom: '6px' }}>{plan.title || 'Lesson Plan'}</h3>
      {plan.overview && (
        <p style={{ color: '#555', fontSize: '14px', marginBottom: '12px' }}>{plan.overview}</p>
      )}

      {plan.objectives && plan.objectives.length > 0 && (
        <div style={{ marginBottom: '14px' }}>
          <strong style={{ color: '#4A8B3F', fontSize: '13px' }}>Learning Objectives</strong>
          <ul style={{ margin: '6px 0 0 18px', padding: 0, fontSize: '13px', color: '#444' }}>
            {plan.objectives.map((obj, i) => <li key={i}>{obj}</li>)}
          </ul>
        </div>
      )}

      {days.map((day, i) => (
        <div key={i} style={{ marginBottom: '8px', border: '1px solid #e0e0e0', borderRadius: '10px', overflow: 'hidden' }}>
          <button
            onClick={() => setOpenDay(openDay === i ? null : i)}
            style={{
              width: '100%', textAlign: 'left', padding: '10px 14px',
              background: openDay === i ? '#6EB4D4' : '#f5f5f5',
              color: openDay === i ? 'white' : '#333',
              border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '14px',
              display: 'flex', justifyContent: 'space-between',
            }}
          >
            <span>{day.day || `Day ${i + 1}`}{day.title ? ` — ${day.title}` : ''}</span>
            <span>{openDay === i ? '▲' : '▼'}</span>
          </button>

          {openDay === i && (
            <div style={{ padding: '12px 14px', fontSize: '13px', color: '#444', background: 'white' }}>
              {day.objective && <p><strong>Objective:</strong> {day.objective}</p>}
              {day.warmup && <p><strong>Warm-up:</strong> {day.warmup}</p>}
              {day.main_activity && <p><strong>Main Activity:</strong> {day.main_activity}</p>}
              {day.practice && <p><strong>Practice:</strong> {day.practice}</p>}
              {day.assessment && <p><strong>Assessment:</strong> {day.assessment}</p>}
              {day.homework && <p><strong>Homework:</strong> {day.homework}</p>}
            </div>
          )}
        </div>
      ))}

      {plan.materials_needed && plan.materials_needed.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <strong style={{ color: '#4A8B3F', fontSize: '13px' }}>Materials Needed</strong>
          <ul style={{ margin: '6px 0 0 18px', padding: 0, fontSize: '13px', color: '#444' }}>
            {plan.materials_needed.map((m, i) => <li key={i}>{m}</li>)}
          </ul>
        </div>
      )}

      {plan.parent_tips && (
        <div style={{ marginTop: '12px', background: '#FFF9C4', borderRadius: '8px', padding: '10px 14px' }}>
          <strong style={{ color: '#B8860B', fontSize: '13px' }}>💛 Parent Tips</strong>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#555' }}>{plan.parent_tips}</p>
        </div>
      )}
    </div>
  )
}
