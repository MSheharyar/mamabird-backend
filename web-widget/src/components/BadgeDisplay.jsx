export default function BadgeDisplay({ badges = [], newBadges = [] }) {
  if (!badges.length && !newBadges.length) return null

  const newTypes = new Set(newBadges.map(b => b.badge_type))

  return (
    <div style={{ overflowX: 'auto', padding: '8px 0' }}>
      <div style={{ display: 'flex', gap: '10px', minWidth: 'max-content' }}>
        {badges.map((badge, i) => (
          <div
            key={badge.id || i}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              background: newTypes.has(badge.badge_type) ? '#FFF9C4' : '#f8f9fa',
              border: newTypes.has(badge.badge_type) ? '2px solid #F5C200' : '1px solid #e0e0e0',
              borderRadius: '12px', padding: '8px 12px', minWidth: '80px',
              animation: newTypes.has(badge.badge_type) ? 'badgePulse 1s ease-in-out 3' : 'none',
            }}
          >
            <span style={{ fontSize: '24px' }}>{badge.badge_emoji}</span>
            <span style={{ fontSize: '11px', color: '#555', textAlign: 'center', marginTop: '4px', fontWeight: 600 }}>
              {badge.badge_name}
            </span>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes badgePulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.15); }
        }
      `}</style>
    </div>
  )
}
