export default function CharacterSelector({ selected, onSelect }) {
  return (
    <div className="character-selector">
      <button
        className={`character-btn ${selected === 'character_1' ? 'active-chirpy' : ''}`}
        onClick={() => onSelect('character_1')}
      >
        🐦
        <span>Chirpy</span>
        <span style={{ fontSize: '11px', fontWeight: 600, opacity: 0.8 }}>(for kids)</span>
      </button>
      <button
        className={`character-btn ${selected === 'character_2' ? 'active-mama' : ''}`}
        onClick={() => onSelect('character_2')}
      >
        🪺
        <span>Mama Bird</span>
        <span style={{ fontSize: '11px', fontWeight: 600, opacity: 0.8 }}>(for parents)</span>
      </button>
    </div>
  )
}
