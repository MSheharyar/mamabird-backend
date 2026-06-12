export default function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  const isCharacter1 = message.character === 'character_1'

  const avatar = isUser ? '👤' : isCharacter1 ? '🐦' : '🪺'
  const name = isUser ? 'You' : isCharacter1 ? 'Chirpy' : 'Mama Bird'

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-end',
      gap: '10px',
      marginBottom: '5px'
    }}>
      {/* Avatar */}
      <div style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        background: '#FFF0F0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '22px',
        flexShrink: 0,
        border: '2px solid #F5C200'
      }}>
        {avatar}
      </div>

      {/* Bubble + name */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '70%'
      }}>
        <div style={{
          fontSize: '11px',
          color: '#888',
          marginBottom: '4px',
          fontWeight: 600
        }}>
          {name}
        </div>

        <div style={{
          padding: '12px 16px',
          borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          fontSize: '15px',
          lineHeight: '1.5',
          minWidth: '60px',
          background: isUser ? '#CC2929' : '#E0F4FF',
          color: isUser ? 'white' : '#1a1a1a',
          border: isUser ? 'none' : '1px solid #6EB4D4',
          textAlign: isUser ? 'center' : 'left'
        }}>
          {message.content}
        </div>

        {message.progress && message.progress.was_correct && (
          <div className="score-badge">
            ✅ Correct! +{message.progress.score} point
          </div>
        )}
      </div>
    </div>
  )
}