import { useState } from 'react'
import axios from 'axios'
import Icon from './Icon'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PLANS = [
  {
    id: 'individual',
    name: 'Individual',
    price: '$6.99',
    period: '/month',
    emoji: '🐣',
    features: ['1 child profile', 'Up to 400 messages/month', 'All subjects + badges', 'Lesson plan generator'],
    highlight: false,
    accentColor: '#6EB4D4',
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '$9.99',
    period: '/month',
    emoji: '🐦',
    features: ['Up to 3 child profiles', '1,000 messages/month', 'Priority AI responses', 'Full progress dashboard'],
    highlight: true,
    accentColor: '#F5C200',
  },
  {
    id: 'classroom',
    name: 'Classroom',
    price: '$19.99',
    period: '/month',
    emoji: '🦅',
    features: ['Up to 30 student profiles', '200 messages per student', 'Teacher dashboard', 'Bulk lesson plans'],
    highlight: false,
    accentColor: '#4A8B3F',
  },
]

export default function PaywallScreen({ token, errorCode, onBack }) {
  const [loading, setPlanLoading] = useState(null)
  const [error, setError] = useState('')

  const handleSubscribe = async (planId) => {
    if (!token) { setError('Please log in first.'); return }
    setPlanLoading(planId)
    setError('')
    try {
      const res = await axios.post(
        `${API_URL}/payments/create-checkout-session`,
        { plan: planId },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      window.location.href = res.data.checkout_url
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to start checkout. Please try again.')
      setPlanLoading(null)
    }
  }

  const isLimitReached = errorCode === 'MESSAGE_LIMIT_REACHED'

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(160deg, #87CEEB 0%, #C8E9F8 60%, #E0F4FF 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px',
    }}>
      <div style={{
        background: 'white', borderRadius: '28px', padding: '44px 40px',
        maxWidth: '800px', width: '100%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.14)', textAlign: 'center',
        animation: 'fadeSlideIn 0.3s ease',
      }}>
        <div style={{ fontSize: '64px', marginBottom: '12px', display: 'block', animation: 'float 3s ease-in-out infinite', lineHeight: 1 }}>🐦</div>
        <h1 style={{ color: '#CC2929', marginBottom: '8px', fontSize: '26px', fontWeight: 800, letterSpacing: '-0.3px' }}>
          {isLimitReached ? "You've reached your message limit!" : 'Your free trial has ended'}
        </h1>
        <p style={{ color: '#888', marginBottom: '36px', fontSize: '15px', fontWeight: 600 }}>
          {isLimitReached
            ? 'Upgrade to keep learning with Chirpy and Mama Bird! 🚀'
            : 'Choose a plan below to continue your learning adventure! 🌟'}
        </p>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '28px' }}>
          {PLANS.map(plan => (
            <div
              key={plan.id}
              style={{
                flex: '1', minWidth: '210px', maxWidth: '230px',
                border: plan.highlight ? `3px solid ${plan.accentColor}` : '2px solid #F0F0F0',
                borderRadius: '20px', padding: '28px 20px',
                background: plan.highlight ? '#FFFDE7' : 'white',
                position: 'relative', transition: 'transform 0.2s, box-shadow 0.2s',
                boxShadow: plan.highlight ? '0 8px 28px rgba(245,194,0,0.2)' : '0 3px 12px rgba(0,0,0,0.06)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-4px)'
                e.currentTarget.style.boxShadow = plan.highlight
                  ? '0 16px 40px rgba(245,194,0,0.25)'
                  : '0 12px 32px rgba(0,0,0,0.12)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'none'
                e.currentTarget.style.boxShadow = plan.highlight
                  ? '0 8px 28px rgba(245,194,0,0.2)'
                  : '0 3px 12px rgba(0,0,0,0.06)'
              }}
            >
              {plan.highlight && (
                <div style={{
                  position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)',
                  background: 'linear-gradient(135deg, #F5C200, #E6B300)',
                  color: '#5C4400', borderRadius: '20px',
                  padding: '4px 16px', fontSize: '11px', fontWeight: 800,
                  letterSpacing: '0.5px', textTransform: 'uppercase',
                  boxShadow: '0 3px 10px rgba(245,194,0,0.4)',
                  whiteSpace: 'nowrap',
                }}>
                  ⭐ Most Popular
                </div>
              )}

              <div style={{ fontSize: '40px', marginBottom: '10px' }}>{plan.emoji}</div>
              <h2 style={{ color: '#CC2929', margin: '0 0 4px', fontSize: '18px', fontWeight: 800 }}>{plan.name}</h2>
              <div style={{ marginBottom: '18px' }}>
                <span style={{ fontSize: '28px', fontWeight: 800, color: '#1E1E1E' }}>{plan.price}</span>
                <span style={{ fontSize: '13px', color: '#aaa', fontWeight: 700 }}>{plan.period}</span>
              </div>

              <ul style={{ textAlign: 'left', padding: '0 0 0 4px', margin: '0 0 22px', fontSize: '13px', color: '#555', listStyle: 'none' }}>
                {plan.features.map((f, i) => (
                  <li key={i} style={{ marginBottom: '8px', display: 'flex', gap: '7px', alignItems: 'flex-start', fontWeight: 600 }}>
                    <span style={{ color: plan.accentColor, fontSize: '14px', marginTop: '1px' }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={loading === plan.id}
                style={{
                  width: '100%', padding: '12px', borderRadius: '12px', border: 'none',
                  background: plan.highlight
                    ? 'linear-gradient(135deg, #F5C200, #E6B300)'
                    : `linear-gradient(135deg, ${plan.accentColor}, ${plan.accentColor}CC)`,
                  color: plan.highlight ? '#5C4400' : 'white',
                  fontFamily: 'inherit', fontWeight: 800, fontSize: '14px',
                  cursor: loading === plan.id ? 'not-allowed' : 'pointer',
                  opacity: loading === plan.id ? 0.7 : 1,
                  transition: 'all 0.18s',
                  boxShadow: `0 4px 14px ${plan.accentColor}44`,
                  letterSpacing: '0.2px',
                }}
              >
                {loading === plan.id ? 'Loading...' : `Subscribe to ${plan.name}`}
              </button>
            </div>
          ))}
        </div>

        {error && (
          <div style={{
            color: '#A82020', background: '#FFF0F0', borderRadius: '10px',
            padding: '10px 16px', fontSize: '13px', fontWeight: 700, marginBottom: '12px',
            border: '1px solid #CC292922', display: 'flex', alignItems: 'center', gap: '8px',
          }}>
            <Icon name="alert" size={15} color="#A82020" />
            {error}
          </div>
        )}

        {onBack && (
          <button
            onClick={onBack}
            style={{
              background: 'none', border: '2px solid #E8E8E8', color: '#aaa',
              cursor: 'pointer', fontSize: '13px', fontFamily: 'inherit',
              fontWeight: 800, borderRadius: '10px', padding: '8px 16px',
              transition: 'all 0.15s', display: 'inline-flex', alignItems: 'center', gap: '6px',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#6EB4D4'; e.currentTarget.style.color = '#6EB4D4' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#E8E8E8'; e.currentTarget.style.color = '#aaa' }}
          >
            <Icon name="arrow-left" size={13} color="currentColor" />
            Go back
          </button>
        )}
      </div>
    </div>
  )
}
