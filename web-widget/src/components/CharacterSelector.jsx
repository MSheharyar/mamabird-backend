export default function CharacterSelector({ selected, onSelect }) {
  return (
    <div className="character-selector">
      <button
        className={`character-btn ${selected === 'character_1' ? 'active' : ''}`}
        onClick={() => onSelect('character_1')}
      >
        🐦 Chirpy
        <span style={{ fontSize: '11px', fontWeight: 'normal' }}>
          (for kids)
        </span>
      </button>
      <button
        className={`character-btn ${selected === 'character_2' ? 'active' : ''}`}
        onClick={() => onSelect('character_2')}
      >
        🪺 Mama Bird
        <span style={{ fontSize: '11px', fontWeight: 'normal' }}>
          (for parents)
        </span>
      </button>
    </div>
  )
}