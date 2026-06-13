import { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PLANS = [
  {
    id: 'individual',
    name: 'Individual',
    price: '$6.99/mo',
    emoji: '🐣',
    features: ['1 child profile', 'Up to 400 messages/month', 'All subjects + badges', 'Lesson plan generator'],
    highlight: false,
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '$9.99/mo',
    emoji: '🐦',
    features: ['Up to 3 child profiles', '1,000 messages/month', 'Priority AI responses', 'Full progress dashboard'],
    highlight: true,
  },
  {
    id: 'classroom',
    name: 'Classroom',
    price: '$19.99/mo',
    emoji: '🦅',
    features: ['Up to 30 student profiles', '200 messages per student', 'Teacher dashboard', 'Bulk lesson plans'],
    highlight: false,
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
      minHeight: '100vh', background: 'linear-gradient(135deg, #6EB4D4 0%, #4A8B3F 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
    }}>
      <div style={{
        background: 'white', borderRadius: '24px', padding: '40px', maxWidth: '780px',
        width: '100%', boxShadow: '0 20px 60px rgba(0,0,0,0.15)', textAlign: 'center',
      }}>
        <div style={{ fontSize: '60px', marginBottom: '10px' }}>🐦</div>
        <h1 style={{ color: '#CC2929', marginBottom: '8px' }}>
          {isLimitReached ? "You've reached your message limit!" : "Your free trial has ended"}
        </h1>
        <p style={{ color: '#666', marginBottom: '32px', fontSize: '16px' }}>
          {isLimitReached
            ? 'Upgrade your plan to keep learning with Chirpy and Mama Bird! 🚀'
            : 'Choose a plan below to continue your learning adventure! 🌟'}
        </p>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
          {PLANS.map(plan => (
            <div
              key={plan.id}
              style={{
                flex: '1', minWidth: '200px', maxWidth: '220px',
                border: plan.highlight ? '3px solid #F5C200' : '2px solid #e0e0e0',
                borderRadius: '16px', padding: '24px 16px',
                background: plan.highlight ? '#FFFDE7' : 'white',
                position: 'relative',
              }}
            >
              {plan.highlight && (
                <div style={{
                  position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)',
                  background: '#F5C200', color: '#333', borderRadius: '20px',
                  padding: '4px 14px', fontSize: '12px', fontWeight: 700,
                }}>
                  MOST POPULAR
                </div>
              )}
              <div style={{ fontSize: '36px', marginBottom: '8px' }}>{plan.emoji}</div>
              <h2 style={{ color: '#CC2929', margin: '0 0 4px' }}>{plan.name}</h2>
              <p style={{ fontSize: '22px', fontWeight: 700, color: '#333', margin: '0 0 16px' }}>{plan.price}</p>
              <ul style={{ textAlign: 'left', padding: '0 0 0 18px', margin: '0 0 20px', fontSize: '13px', color: '#555' }}>
                {plan.features.map((f, i) => <li key={i} style={{ marginBottom: '6px' }}>{f}</li>)}
              </ul>
              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={loading === plan.id}
                style={{
                  width: '100%', padding: '12px', borderRadius: '10px', border: 'none',
                  background: plan.highlight ? '#F5C200' : '#6EB4D4',
                  color: plan.highlight ? '#333' : 'white',
                  fontWeight: 700, fontSize: '15px', cursor: loading === plan.id ? 'not-allowed' : 'pointer',
                  opacity: loading === plan.id ? 0.7 : 1,
                }}
              >
                {loading === plan.id ? 'Loading...' : 'Subscribe'}
              </button>
            </div>
          ))}
        </div>

        {error && (
          <p style={{ color: '#CC2929', marginTop: '16px', fontSize: '14px' }}>{error}</p>
        )}

        {onBack && (
          <button
            onClick={onBack}
            style={{
              marginTop: '20px', background: 'none', border: 'none', color: '#888',
              cursor: 'pointer', fontSize: '14px', textDecoration: 'underline',
            }}
          >
            ← Go back
          </button>
        )}
      </div>
    </div>
  )
}
