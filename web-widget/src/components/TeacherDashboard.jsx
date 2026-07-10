import { useState, useEffect } from 'react'
import axios from 'axios'
import Icon from './Icon'
import LessonPlanViewer from './LessonPlanViewer'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const SUBJECTS = ['spelling', 'math', 'rhyming', 'grammar', 'puzzles', 'literature']
const DURATIONS = ['3 days', '5 days', '1 week', '2 weeks']

const C = {
  red: '#CC2929', green: '#4A8B3F', blue: '#6EB4D4', amber: '#F5C200',
  dark: '#1E1E1E', mid: '#666', line: '#E8E8E8', cream: '#FAFAFA',
}

const S = {
  page: { width: 'calc(100vw - 40px)', maxWidth: '980px', minHeight: '92vh', background: 'white',
    borderRadius: '28px', boxShadow: '0 12px 48px rgba(0,0,0,0.14)', overflow: 'auto', border: '1px solid rgba(255,255,255,0.9)' },
  header: { display: 'flex', alignItems: 'center', gap: '12px', padding: '20px 26px', borderBottom: `1px solid ${C.line}`,
    position: 'sticky', top: 0, background: 'white', zIndex: 5 },
  h1: { fontSize: '20px', fontWeight: 800, color: C.red, margin: 0 },
  body: { padding: '22px 26px 40px' },
  btn: { border: 'none', borderRadius: '10px', padding: '9px 15px', fontFamily: 'inherit', fontWeight: 700,
    fontSize: '13px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' },
  card: { background: 'white', border: `1px solid ${C.line}`, borderRadius: '16px', padding: '18px', cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(0,0,0,0.05)', transition: 'all .15s' },
  stat: { flex: 1, background: C.cream, borderRadius: '14px', padding: '14px 16px', borderLeft: `4px solid ${C.blue}` },
  statVal: { fontSize: '24px', fontWeight: 800 },
  statLbl: { fontSize: '11px', color: C.mid, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.5px' },
  th: { textAlign: 'left', fontSize: '11px', color: C.mid, fontWeight: 800, textTransform: 'uppercase',
    letterSpacing: '.5px', padding: '8px 10px', borderBottom: `2px solid ${C.line}` },
  td: { padding: '10px', fontSize: '13px', color: C.dark, borderBottom: `1px solid ${C.line}` },
  input: { width: '100%', padding: '11px 14px', border: `2px solid ${C.line}`, borderRadius: '11px',
    fontFamily: 'inherit', fontSize: '14px', fontWeight: 600, background: C.cream, color: C.dark, outline: 'none', boxSizing: 'border-box' },
  label: { display: 'block', fontSize: '12px', fontWeight: 800, color: '#555', margin: '0 0 5px',
    textTransform: 'uppercase', letterSpacing: '.5px' },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center',
    justifyContent: 'center', zIndex: 50, padding: '20px' },
  modal: { background: 'white', borderRadius: '20px', padding: '26px', width: '100%', maxWidth: '440px',
    boxShadow: '0 16px 48px rgba(0,0,0,0.25)' },
}

const accColor = (a) => (a >= 80 ? C.green : a >= 50 ? '#B8860B' : C.red)

export default function TeacherDashboard({ token, onLogout, onTeachStudent }) {
  const auth = { headers: { Authorization: `Bearer ${token}` } }
  const [view, setView] = useState('list')          // 'list' | 'detail'
  const [classes, setClasses] = useState([])
  const [active, setActive] = useState(null)         // { id, name, grade_level }
  const [analytics, setAnalytics] = useState(null)
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  // modals
  const [showNewClass, setShowNewClass] = useState(false)
  const [newClass, setNewClass] = useState({ name: '', grade_level: '' })
  const [showAddStudent, setShowAddStudent] = useState(false)
  const [newStudent, setNewStudent] = useState({ child_name: '', age: '', grade: '' })
  const [showAssign, setShowAssign] = useState(false)
  const [assignForm, setAssignForm] = useState({ subject: 'spelling', grade: '', duration: '5 days', focus_areas: '' })
  const [assigning, setAssigning] = useState(false)
  const [viewingPlan, setViewingPlan] = useState(null)

  const fail = (e) => setErr(e?.response?.data?.detail?.message || e?.response?.data?.detail || 'Something went wrong.')

  const loadClasses = async () => {
    setLoading(true); setErr('')
    try { const r = await axios.get(`${API_URL}/classrooms`, auth); setClasses(r.data.classrooms || []) }
    catch (e) { fail(e) } finally { setLoading(false) }
  }
  useEffect(() => { loadClasses() }, [])

  const openClass = async (cls) => {
    setActive(cls); setView('detail'); setAnalytics(null); setLessons([]); setErr('')
    try {
      const [a, l] = await Promise.all([
        axios.get(`${API_URL}/classrooms/${cls.id}/analytics`, auth),
        axios.get(`${API_URL}/classrooms/${cls.id}/lessons`, auth),
      ])
      setAnalytics(a.data); setLessons(l.data.lesson_plans || [])
    } catch (e) { fail(e) }
  }
  const refreshDetail = () => active && openClass(active)

  const createClass = async () => {
    if (!newClass.name.trim()) return
    try {
      await axios.post(`${API_URL}/classrooms`, { name: newClass.name, grade_level: newClass.grade_level || null }, auth)
      setShowNewClass(false); setNewClass({ name: '', grade_level: '' }); loadClasses()
    } catch (e) { fail(e) }
  }
  const deleteClass = async (cls) => {
    if (!window.confirm(`Delete class "${cls.name}"? Students stay in your account but are unassigned.`)) return
    try { await axios.delete(`${API_URL}/classrooms/${cls.id}`, auth); setView('list'); loadClasses() }
    catch (e) { fail(e) }
  }
  const addStudent = async () => {
    if (!newStudent.child_name.trim()) return
    try {
      await axios.post(`${API_URL}/classrooms/${active.id}/students`,
        { child_name: newStudent.child_name, age: newStudent.age ? Number(newStudent.age) : null, grade: newStudent.grade || null }, auth)
      setShowAddStudent(false); setNewStudent({ child_name: '', age: '', grade: '' }); refreshDetail()
    } catch (e) { fail(e) }
  }
  const removeStudent = async (sid, name) => {
    if (!window.confirm(`Remove ${name} from this class?`)) return
    try { await axios.delete(`${API_URL}/classrooms/${active.id}/students/${sid}`, auth); refreshDetail() }
    catch (e) { fail(e) }
  }
  const assignLesson = async () => {
    setAssigning(true); setErr('')
    try {
      await axios.post(`${API_URL}/classrooms/${active.id}/assign-lesson`, assignForm, auth)
      setShowAssign(false); refreshDetail()
    } catch (e) { fail(e) } finally { setAssigning(false) }
  }
  const regenCode = async () => {
    if (!window.confirm('Generate a new code? The current one stops working immediately.')) return
    try { const r = await axios.post(`${API_URL}/classrooms/${active.id}/regenerate-code`, {}, auth); setActive({ ...active, join_code: r.data.join_code }) }
    catch (e) { fail(e) }
  }
  const downloadReport = async () => {
    try {
      const r = await axios.get(`${API_URL}/classrooms/${active.id}/report-pdf`, { ...auth, responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url; a.download = `class_report_${(active.name || 'class').replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
    } catch (e) { fail(e) }
  }

  // ── Shell ──────────────────────────────────────────────────────────
  const shell = (children) => (
    <div style={S.page}>
      <div style={S.header}>
        <div style={{ width: 34, height: 34, borderRadius: 9, background: C.red, display: 'flex',
          alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🐦</div>
        <div style={{ marginRight: 'auto' }}>
          <h1 style={S.h1}>Teacher Dashboard</h1>
          <div style={{ fontSize: 12, color: C.mid, fontWeight: 600 }}>MamaBird &amp; Chirpy · Classroom</div>
        </div>
        <button style={{ ...S.btn, background: '#FFF0F0', color: C.red, border: `1.5px solid #CC292933` }} onClick={onLogout}>
          <Icon name="x" size={12} color={C.red} /> Log out
        </button>
      </div>
      <div style={S.body}>
        {err && <div style={{ background: '#FFF0F0', color: C.red, padding: '10px 14px', borderRadius: 10,
          fontWeight: 700, fontSize: 13, marginBottom: 16 }}>⚠️ {err}</div>}
        {children}
      </div>
    </div>
  )

  // ── List view ─────────────────────────────────────────────────────
  if (view === 'list') {
    return shell(
      <>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 18 }}>
          <h2 style={{ fontSize: 16, fontWeight: 800, color: C.dark, margin: 0, marginRight: 'auto' }}>Your Classes</h2>
          <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.green}, #3A7030)`, color: 'white' }}
            onClick={() => setShowNewClass(true)}>
            <Icon name="zap" size={13} color="white" /> New Class
          </button>
        </div>

        {loading ? <p style={{ color: C.mid }}>Loading…</p>
          : classes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 20px', color: C.mid }}>
              <div style={{ fontSize: 44 }}>🏫</div>
              <p style={{ fontWeight: 700, marginTop: 10 }}>No classes yet</p>
              <p style={{ fontSize: 13 }}>Create your first class to add students and track progress.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 14 }}>
              {classes.map((c) => (
                <div key={c.id} style={S.card} onClick={() => openClass(c)}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = C.blue; e.currentTarget.style.transform = 'translateY(-2px)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = C.line; e.currentTarget.style.transform = 'none' }}>
                  <div style={{ fontSize: 26 }}>📚</div>
                  <div style={{ fontWeight: 800, color: C.dark, fontSize: 15, marginTop: 6 }}>{c.name}</div>
                  <div style={{ fontSize: 12, color: C.mid, fontWeight: 600, marginTop: 2 }}>
                    {c.grade_level ? `${c.grade_level} · ` : ''}{c.student_count} student{c.student_count === 1 ? '' : 's'}
                  </div>
                </div>
              ))}
            </div>
          )}

        {showNewClass && (
          <div style={S.overlay} onClick={() => setShowNewClass(false)}>
            <div style={S.modal} onClick={(e) => e.stopPropagation()}>
              <h3 style={{ margin: '0 0 18px', color: C.dark, fontWeight: 800 }}>🏫 New Class</h3>
              <div style={{ marginBottom: 14 }}>
                <label style={S.label}>Class name</label>
                <input style={S.input} placeholder="e.g. Grade 1 - Room A" value={newClass.name}
                  onChange={(e) => setNewClass({ ...newClass, name: e.target.value })} />
              </div>
              <div style={{ marginBottom: 20 }}>
                <label style={S.label}>Grade level (optional)</label>
                <input style={S.input} placeholder="Grade 1" value={newClass.grade_level}
                  onChange={(e) => setNewClass({ ...newClass, grade_level: e.target.value })} />
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button style={{ ...S.btn, background: '#F0F0F0', color: '#555', flex: 1, justifyContent: 'center' }}
                  onClick={() => setShowNewClass(false)}>Cancel</button>
                <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.red}, #A82020)`, color: 'white', flex: 1, justifyContent: 'center' }}
                  onClick={createClass}>Create</button>
              </div>
            </div>
          </div>
        )}
      </>
    )
  }

  // ── Detail view ───────────────────────────────────────────────────
  const t = analytics?.totals || {}
  const students = analytics?.students || []
  const subjects = analytics?.subject_breakdown || {}

  return shell(
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
        <button style={{ ...S.btn, background: '#F0F0F0', color: '#555' }} onClick={() => { setView('list'); loadClasses() }}>← Classes</button>
        <h2 style={{ fontSize: 17, fontWeight: 800, color: C.dark, margin: 0, marginRight: 'auto' }}>
          {active?.name}{active?.grade_level ? <span style={{ color: C.mid, fontWeight: 600, fontSize: 13 }}> · {active.grade_level}</span> : null}
        </h2>
        <button style={{ ...S.btn, background: C.cream, color: C.dark, border: `1px solid ${C.line}` }} onClick={downloadReport}>
          <Icon name="download" size={13} color={C.dark} /> Class Report
        </button>
        <button style={{ ...S.btn, background: '#FFF0F0', color: C.red, border: '1px solid #CC292933' }} onClick={() => deleteClass(active)}>Delete</button>
      </div>

      {active?.join_code && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', margin: '-4px 0 18px' }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: C.mid }}>🔑 Join code:</span>
          <span style={{ fontFamily: 'monospace', fontWeight: 800, fontSize: 16, letterSpacing: 3, background: '#EBF6FC', color: '#3A8BB0', padding: '4px 12px', borderRadius: 8 }}>{active.join_code}</span>
          <button style={{ ...S.btn, background: C.cream, color: C.dark, border: `1px solid ${C.line}` }} onClick={() => { navigator.clipboard && navigator.clipboard.writeText(active.join_code) }}>Copy</button>
          <button style={{ ...S.btn, background: C.cream, color: C.dark, border: `1px solid ${C.line}` }} onClick={regenCode}>Regenerate</button>
          <span style={{ fontSize: 12, color: C.mid, flexBasis: '100%' }}>Share with parents so they can enroll their child in this class.</span>
        </div>
      )}

      {!analytics ? <p style={{ color: C.mid }}>Loading class data…</p> : (
        <>
          {/* totals */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 22, flexWrap: 'wrap' }}>
            <div style={{ ...S.stat, borderLeftColor: C.blue }}><div style={{ ...S.statVal, color: C.blue }}>{t.students || 0}</div><div style={S.statLbl}>Students</div></div>
            <div style={{ ...S.stat, borderLeftColor: C.green }}><div style={{ ...S.statVal, color: C.green }}>{t.accuracy_pct || 0}%</div><div style={S.statLbl}>Class Accuracy</div></div>
            <div style={{ ...S.stat, borderLeftColor: C.red }}><div style={{ ...S.statVal, color: C.red }}>{t.sessions || 0}</div><div style={S.statLbl}>Sessions</div></div>
            <div style={{ ...S.stat, borderLeftColor: C.amber }}><div style={{ ...S.statVal, color: '#B8860B' }}>{t.badges || 0}</div><div style={S.statLbl}>Badges</div></div>
          </div>

          {/* roster */}
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 10 }}>
            <h3 style={{ fontSize: 14, fontWeight: 800, color: C.red, margin: 0, marginRight: 'auto', textTransform: 'uppercase', letterSpacing: '.5px' }}>Roster</h3>
            <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.green}, #3A7030)`, color: 'white' }} onClick={() => setShowAddStudent(true)}>
              <Icon name="user" size={12} color="white" /> Add Student
            </button>
          </div>
          <div style={{ overflowX: 'auto', marginBottom: 26 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 560 }}>
              <thead><tr>
                <th style={S.th}>Student</th><th style={S.th}>Grade</th><th style={S.th}>Sessions</th>
                <th style={S.th}>Accuracy</th><th style={S.th}>Badges</th><th style={S.th}></th>
              </tr></thead>
              <tbody>
                {students.length === 0 ? (
                  <tr><td style={{ ...S.td, color: C.mid }} colSpan={6}>No students yet — add one to get started.</td></tr>
                ) : students.map((s) => (
                  <tr key={s.id}>
                    <td style={{ ...S.td, fontWeight: 700 }}>🐣 {s.child_name}{s.joined && <span style={{ fontSize: 10, background: '#FFFAEB', color: '#92600a', padding: '2px 7px', borderRadius: 999, fontWeight: 700, marginLeft: 6, verticalAlign: 'middle' }}>parent-joined</span>}</td>
                    <td style={S.td}>{s.grade || '—'}</td>
                    <td style={S.td}>{s.sessions}</td>
                    <td style={{ ...S.td, fontWeight: 800, color: accColor(s.avg_score) }}>{s.avg_score}%</td>
                    <td style={S.td}>{s.badges}</td>
                    <td style={{ ...S.td, whiteSpace: 'nowrap' }}>
                      {s.joined
                        ? <span style={{ fontSize: 12, color: C.mid }}>Parent-managed</span>
                        : <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.blue}, #4A96BC)`, color: 'white', padding: '6px 10px', fontSize: 12 }}
                            onClick={() => onTeachStudent && onTeachStudent({ id: s.id, child_name: s.child_name })}>▶ Teach</button>}
                      <button style={{ ...S.btn, background: 'none', color: C.mid, padding: '6px 8px', fontSize: 12 }}
                        onClick={() => removeStudent(s.id, s.child_name)}>Remove</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* subject breakdown */}
          <h3 style={{ fontSize: 14, fontWeight: 800, color: C.red, margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '.5px' }}>Class Progress by Subject</h3>
          {Object.keys(subjects).length === 0 ? (
            <p style={{ color: C.mid, fontSize: 13, marginBottom: 26 }}>No subject data recorded yet.</p>
          ) : (
            <div style={{ marginBottom: 26 }}>
              {Object.entries(subjects).sort().map(([subj, v]) => (
                <div key={subj} style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', fontSize: 13, fontWeight: 700, color: C.dark, marginBottom: 4 }}>
                    <span style={{ textTransform: 'capitalize', marginRight: 'auto' }}>{subj}</span>
                    <span style={{ color: accColor(v.accuracy_pct) }}>{v.accuracy_pct}% · {v.correct}/{v.total}</span>
                  </div>
                  <div style={{ height: 8, background: '#EDEDED', borderRadius: 5, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${Math.min(v.accuracy_pct, 100)}%`, background: C.blue, borderRadius: 5 }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* lessons */}
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 10 }}>
            <h3 style={{ fontSize: 14, fontWeight: 800, color: C.red, margin: 0, marginRight: 'auto', textTransform: 'uppercase', letterSpacing: '.5px' }}>Assigned Lessons</h3>
            <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.amber}, #d9a900)`, color: '#5a4600' }}
              onClick={() => { setAssignForm({ ...assignForm, grade: active?.grade_level || '' }); setShowAssign(true) }}>
              <Icon name="book-open" size={12} color="#5a4600" /> Assign Lesson
            </button>
          </div>
          {lessons.length === 0 ? (
            <p style={{ color: C.mid, fontSize: 13 }}>No lessons assigned yet.</p>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              {lessons.map((l) => (
                <div key={l.id} style={{ border: `1px solid ${C.line}`, borderRadius: 12, padding: '12px 14px',
                  display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ marginRight: 'auto' }}>
                    <div style={{ fontWeight: 700, color: C.dark, fontSize: 14 }}>{l.title}</div>
                    <div style={{ fontSize: 12, color: C.mid }}>{String(l.created_at || '').slice(0, 10)}</div>
                  </div>
                  <button style={{ ...S.btn, background: C.cream, color: C.dark, border: `1px solid ${C.line}` }}
                    onClick={() => setViewingPlan(l.plan_data)}>View</button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Add Student modal */}
      {showAddStudent && (
        <div style={S.overlay} onClick={() => setShowAddStudent(false)}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 18px', color: C.dark, fontWeight: 800 }}>🐣 Add Student</h3>
            <div style={{ marginBottom: 14 }}>
              <label style={S.label}>Nickname</label>
              <input style={S.input} placeholder="e.g. Emma" value={newStudent.child_name}
                onChange={(e) => setNewStudent({ ...newStudent, child_name: e.target.value })} />
            </div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
              <div style={{ flex: 1 }}>
                <label style={S.label}>Age</label>
                <input style={S.input} placeholder="6" value={newStudent.age}
                  onChange={(e) => setNewStudent({ ...newStudent, age: e.target.value.replace(/\D/g, '') })} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={S.label}>Grade</label>
                <input style={S.input} placeholder="Grade 1" value={newStudent.grade}
                  onChange={(e) => setNewStudent({ ...newStudent, grade: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button style={{ ...S.btn, background: '#F0F0F0', color: '#555', flex: 1, justifyContent: 'center' }} onClick={() => setShowAddStudent(false)}>Cancel</button>
              <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.green}, #3A7030)`, color: 'white', flex: 1, justifyContent: 'center' }} onClick={addStudent}>Add</button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Lesson modal */}
      {showAssign && (
        <div style={S.overlay} onClick={() => !assigning && setShowAssign(false)}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 18px', color: C.dark, fontWeight: 800 }}>📖 Assign Lesson to Class</h3>
            <div style={{ marginBottom: 14 }}>
              <label style={S.label}>Subject</label>
              <select style={S.input} value={assignForm.subject} onChange={(e) => setAssignForm({ ...assignForm, subject: e.target.value })}>
                {SUBJECTS.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
              <div style={{ flex: 1 }}>
                <label style={S.label}>Grade</label>
                <input style={S.input} placeholder="Grade 1" value={assignForm.grade}
                  onChange={(e) => setAssignForm({ ...assignForm, grade: e.target.value })} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={S.label}>Duration</label>
                <select style={S.input} value={assignForm.duration} onChange={(e) => setAssignForm({ ...assignForm, duration: e.target.value })}>
                  {DURATIONS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={S.label}>Focus areas (optional)</label>
              <input style={S.input} placeholder="e.g. sight words, addition" value={assignForm.focus_areas}
                onChange={(e) => setAssignForm({ ...assignForm, focus_areas: e.target.value })} />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button style={{ ...S.btn, background: '#F0F0F0', color: '#555', flex: 1, justifyContent: 'center' }}
                disabled={assigning} onClick={() => setShowAssign(false)}>Cancel</button>
              <button style={{ ...S.btn, background: `linear-gradient(135deg, ${C.red}, #A82020)`, color: 'white', flex: 1, justifyContent: 'center', opacity: assigning ? 0.7 : 1 }}
                disabled={assigning} onClick={assignLesson}>{assigning ? 'Generating…' : 'Generate & Assign'}</button>
            </div>
          </div>
        </div>
      )}

      {/* View plan modal */}
      {viewingPlan && (
        <div style={S.overlay} onClick={() => setViewingPlan(null)}>
          <div style={{ ...S.modal, maxWidth: 640, maxHeight: '86vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button style={{ ...S.btn, background: '#F0F0F0', color: '#555' }} onClick={() => setViewingPlan(null)}>✕ Close</button>
            </div>
            <LessonPlanViewer plan={viewingPlan} />
          </div>
        </div>
      )}
    </>
  )
}
