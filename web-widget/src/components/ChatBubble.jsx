export default function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  const isCharacter1 = message.character === 'character_1'

  const avatar = isUser ? '👤' : isCharacter1 ? '🐦' : '🪺'
  const name = isUser ? 'You' : isCharacter1 ? 'Chirpy' : 'Mama Bird'

  return (
    <div className={`message-row ${isUser ? 'user-row' : ''}`}>
      <div className="bubble-avatar">{avatar}</div>

      <div className="bubble-content">
        <div className="bubble-name">{name}</div>

        <div className={`bubble ${isUser ? 'user-bubble' : 'character-bubble'}`}>
          {message.content}
        </div>

        {message.progress?.was_correct && (
          <div className="score-badge">
            ✅ Correct! +{message.progress.score} point
          </div>
        )}

        {message.newBadges?.length > 0 && (
          <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {message.newBadges.map((badge, i) => (
              <div key={i} style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '5px 12px',
                background: 'linear-gradient(135deg, #FFFBEA, #FFF3C0)',
                border: '1.5px solid #F5C200',
                borderRadius: '20px', fontSize: '12px', fontWeight: 800,
                color: '#7A5C00',
                boxShadow: '0 2px 8px rgba(245,194,0,0.3)',
                animation: 'pulse 1.5s ease 3',
              }}>
                <span style={{ fontSize: '16px' }}>{badge.badge_emoji || '🏅'}</span>
                <span>New badge: {badge.badge_name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
