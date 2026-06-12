const SUBJECTS = [
  { id: 'spelling', label: '📝 Spelling' },
  { id: 'math', label: '🔢 Math' },
  { id: 'rhyming', label: '🎵 Rhyming' },
  { id: 'grammar', label: '📖 Grammar' },
  { id: 'puzzles', label: '🧩 Puzzles' },
  { id: 'literature', label: '📚 Literature' },
]

export default function SubjectSelector({ selected, onSelect }) {
  return (
    <div className="subject-selector">
      {SUBJECTS.map(subject => (
        <button
          key={subject.id}
          className={`subject-pill ${selected === subject.id ? 'active' : ''}`}
          onClick={() => onSelect(subject.id)}
        >
          {subject.label}
        </button>
      ))}
    </div>
  )
}