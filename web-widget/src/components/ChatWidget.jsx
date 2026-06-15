import { useState, useRef, useEffect } from 'react'
import CharacterSelector from './CharacterSelector'
import SubjectSelector from './SubjectSelector'
import ChatBubble from './ChatBubble'
import PaywallScreen from './PaywallScreen'
import ParentDashboard from './ParentDashboard'
import AdminPanel from './AdminPanel'
import IrisDashboard from './IrisDashboard'
import Icon from './Icon'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const S = {
  // Login / Profile Picker card wrapper
  centeredContainer: {
    display: 'flex', justifyContent: 'center', alignItems: 'center',
    minHeight: '100vh', width: 'calc(100vw - 40px)', padding: '24px',
  },
  card: {
    background: 'white', borderRadius: '24px', padding: '44px 40px',
    width: '100%', maxWidth: '420px',
    boxShadow: '0 16px 48px rgba(0,0,0,0.13), 0 2px 8px rgba(0,0,0,0.07)',
    textAlign: 'center',
    animation: 'fadeSlideIn 0.3s ease',
  },
  logoEmoji: {
    fontSize: '68px', lineHeight: 1, display: 'block',
    marginBottom: '12px',
    filter: 'drop-shadow(0 4px 8px rgba(204,41,41,0.2))',
    animation: 'float 3s ease-in-out infinite',
  },
  cardTitle: {
    color: '#CC2929', fontSize: '26px', fontWeight: 800,
    marginBottom: '4px', letterSpacing: '-0.3px',
  },
  cardSubtitle: { color: '#999', marginBottom: '28px', fontSize: '14px', fontWeight: 600 },
  inputLabel: {
    display: 'block', textAlign: 'left', fontSize: '12px',
    fontWeight: 800, color: '#555', marginBottom: '5px',
    textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  inputWrap: { marginBottom: '14px', textAlign: 'left' },
  loginInput: {
    width: '100%', padding: '12px 16px',
    border: '2px solid #E8E8E8', borderRadius: '12px',
    fontFamily: 'inherit', fontSize: '14px', fontWeight: 600,
    outline: 'none', background: '#FAFAFA', color: '#1E1E1E',
    transition: 'border-color 0.18s, box-shadow 0.18s',
  },
  loginError: {
    color: '#CC2929', fontSize: '13px', marginBottom: '14px',
    background: '#FFF0F0', borderRadius: '8px', padding: '8px 12px',
    fontWeight: 700,
  },
  loginBtn: {
    width: '100%', padding: '14px', borderRadius: '12px',
    background: 'linear-gradient(135deg, #CC2929, #A82020)',
    color: 'white', border: 'none', fontFamily: 'inherit',
    fontSize: '15px', fontWeight: 800, cursor: 'pointer',
    boxShadow: '0 4px 16px rgba(204,41,41,0.35)',
    transition: 'all 0.18s',
    letterSpacing: '0.2px',
  },
  cardNote: { marginTop: '20px', fontSize: '12px', color: '#bbb', fontWeight: 600 },

  // Profile picker card button
  profileBtn: {
    width: '100%', marginBottom: '10px', padding: '14px 18px',
    background: 'white', border: '2px solid #E8E8E8', borderRadius: '14px',
    fontFamily: 'inherit', fontSize: '15px', fontWeight: 700,
    color: '#1E1E1E', cursor: 'pointer', textAlign: 'left',
    display: 'flex', alignItems: 'center', gap: '12px',
    transition: 'all 0.18s',
    boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
  },

  // Header right section
  profileChip: {
    display: 'flex', alignItems: 'center', gap: '6px',
    background: 'linear-gradient(135deg, #E8F5E4, #D4EDCF)',
    color: '#3A7030', padding: '4px 10px', borderRadius: '20px',
    fontSize: '12px', fontWeight: 800, marginBottom: '5px',
    border: '1px solid rgba(74,139,63,0.2)',
  },
  headerBtns: { display: 'flex', gap: '6px', justifyContent: 'flex-end', alignItems: 'center' },
  switchBtn: {
    fontSize: '11px', color: '#999', background: 'none',
    border: '1px solid #E8E8E8', borderRadius: '8px',
    padding: '4px 8px', cursor: 'pointer', fontFamily: 'inherit',
    fontWeight: 700, transition: 'all 0.15s',
  },
  logoutBtn: {
    fontSize: '11px', color: '#CC2929', background: 'none',
    border: '1.5px solid #CC292933', borderRadius: '8px',
    padding: '4px 8px', cursor: 'pointer', fontFamily: 'inherit',
    fontWeight: 800, display: 'flex', alignItems: 'center', gap: '4px',
    transition: 'all 0.15s',
  },
  dashBtn: {
    fontSize: '11px', color: 'white', fontFamily: 'inherit',
    background: 'linear-gradient(135deg, #4A8B3F, #3A7030)',
    border: 'none', borderRadius: '8px', padding: '5px 10px',
    cursor: 'pointer', fontWeight: 800,
    boxShadow: '0 2px 8px rgba(74,139,63,0.3)',
    transition: 'all 0.15s',
  },
  adminBtn: {
    fontSize: '11px', color: 'white', fontFamily: 'inherit',
    background: 'linear-gradient(135deg, #CC2929, #A82020)',
    border: 'none', borderRadius: '8px', padding: '5px 10px',
    cursor: 'pointer', fontWeight: 800,
    boxShadow: '0 2px 8px rgba(204,41,41,0.3)',
    transition: 'all 0.15s',
  },
}

export default function ChatWidget() {
  const [character, setCharacter] = useState('character_1')
  const [subject, setSubject] = useState('spelling')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [token, setToken] = useState(null)
  const [showLogin, setShowLogin] = useState(true)
  const [loginData, setLoginData] = useState({ email: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [profiles, setProfiles] = useState([])
  const [selectedProfileId, setSelectedProfileId] = useState(null)
  const [showProfilePicker, setShowProfilePicker] = useState(false)
  const [view, setView] = useState('chat') // 'chat' | 'dashboard' | 'paywall' | 'admin' | 'iris'
  const [currentUserRole, setCurrentUserRole] = useState(null)
  const [paywallErrorCode, setPaywallErrorCode] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    try {
      const res = await axios.post(`${API_URL}/auth/login`, loginData)
      const tok = res.data.token
      const role = res.data.user?.role || null
      setToken(tok)
      setCurrentUserRole(role)

      // Admin users go straight to the Iris dashboard — skip chatbot entirely
      if (role === 'admin') {
        setShowLogin(false)
        setView('iris')
        return
      }

      const profileRes = await axios.get(`${API_URL}/profiles/`, {
        headers: { Authorization: `Bearer ${tok}` }
      })
      const loadedProfiles = profileRes.data.profiles || []
      setProfiles(loadedProfiles)

      if (loadedProfiles.length === 1) {
        setSelectedProfileId(loadedProfiles[0].id)
        setShowLogin(false)
        setWelcomeMessage(character, loadedProfiles[0].child_name)
      } else if (loadedProfiles.length > 1) {
        setShowLogin(false)
        setShowProfilePicker(true)
      } else {
        setShowLogin(false)
        setMessages([{
          role: 'assistant',
          character: character,
          content: "Welcome! 🐦 It looks like you don't have any child profiles yet. Please create one to get started!"
        }])
      }
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Invalid email or password. Try: test@parent.com / Test1234!')
    }
  }

  const setWelcomeMessage = (char, childName) => {
    setMessages([{
      role: 'assistant',
      character: char,
      content: char === 'character_1'
        ? `Tweet tweet! 🐦 Hi ${childName || 'there'}! I'm so excited to learn with you today! Pick a subject above and let's go! ⭐`
        : `Welcome! 🪺 I'm here to help with lesson plans and learning tips. How can I help today? 💛`
    }])
  }

  const handleProfileSelect = (profileId) => {
    const profile = profiles.find(p => p.id === profileId)
    setSelectedProfileId(profileId)
    setShowProfilePicker(false)
    setWelcomeMessage(character, profile?.child_name)
  }

  const handleCharacterChange = (newCharacter) => {
    setCharacter(newCharacter)
    if (token) {
      setMessages([{
        role: 'assistant',
        character: newCharacter,
        content: newCharacter === 'character_1'
          ? `Tweet tweet! 🐦 Hi! Ready to learn something amazing today? Pick a subject and let's fly! ⭐`
          : `Hello! 🪺 How can I support your child's learning journey today? 💛`
      }])
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isThinking) return
    if (!selectedProfileId) {
      setMessages(prev => [...prev, {
        role: 'assistant', character: character,
        content: "Please select a child profile first! 🐦"
      }])
      return
    }

    const userMessage = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsThinking(true)

    try {
      const res = await axios.post(
        `${API_URL}/chat`,
        { child_profile_id: selectedProfileId, character, subject, message: userMessage.content },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const newBadges = res.data.new_badges || []
      setMessages(prev => [...prev, {
        role: 'assistant', character,
        content: res.data.response,
        progress: res.data.progress,
        illustration: res.data.illustration_key,
        newBadges,
      }])
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 402) {
        setPaywallErrorCode(typeof detail === 'object' ? detail.code : 'SUBSCRIPTION_REQUIRED')
        setView('paywall')
        return
      }
      const errorMsg = typeof detail === 'object' ? detail.message : (detail || "Tweet tweet! 🐦 Something went wrong. Please try again!")
      setMessages(prev => [...prev, {
        role: 'assistant', character,
        content: typeof errorMsg === 'string' ? errorMsg : "Something went wrong. Please try again!"
      }])
    } finally {
      setIsThinking(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const handleLogout = () => {
    setToken(null)
    setCurrentUserRole(null)
    setProfiles([])
    setSelectedProfileId(null)
    setMessages([])
    setShowLogin(true)
    setShowProfilePicker(false)
    setView('chat')
    setLoginData({ email: '', password: '' })
    setLoginError('')
  }

  // ─── Iris Admin Dashboard ─────────────────────────────────────────
  if (view === 'iris') return <IrisDashboard token={token} onLogout={handleLogout} />

  const cardWrap = (children) => (
    <div style={{
      width: 'calc(100vw - 40px)', maxWidth: '820px', minHeight: '92vh',
      background: 'white', borderRadius: '28px',
      boxShadow: '0 12px 48px rgba(0,0,0,0.14), 0 2px 8px rgba(0,0,0,0.08)',
      overflow: 'auto', border: '1px solid rgba(255,255,255,0.9)',
    }}>
      {children}
    </div>
  )

  // ─── Admin ────────────────────────────────────────────────────────
  if (view === 'admin') return cardWrap(<AdminPanel token={token} onBack={() => setView('chat')} />)

  // ─── Paywall ──────────────────────────────────────────────────────
  if (view === 'paywall') return <PaywallScreen token={token} errorCode={paywallErrorCode} onBack={() => setView('chat')} />

  // ─── Dashboard ────────────────────────────────────────────────────
  if (view === 'dashboard') return cardWrap(<ParentDashboard token={token} selectedProfileId={selectedProfileId} onBack={() => setView('chat')} />)

  // ─── Login ────────────────────────────────────────────────────────
  if (showLogin) {
    return (
      <div style={S.centeredContainer}>
        <div style={S.card}>
          <span style={S.logoEmoji}>🐦</span>
          <h1 style={S.cardTitle}>MamaBird & Chirpy</h1>
          <p style={S.cardSubtitle}>AI Educational Chatbot</p>

          <form onSubmit={handleLogin}>
            <div style={S.inputWrap}>
              <label style={S.inputLabel}>Email address</label>
              <input
                type="email"
                value={loginData.email}
                onChange={e => setLoginData(prev => ({ ...prev, email: e.target.value }))}
                style={S.loginInput}
                placeholder="you@example.com"
                required
              />
            </div>
            <div style={{ ...S.inputWrap, marginBottom: '20px' }}>
              <label style={S.inputLabel}>Password</label>
              <input
                type="password"
                value={loginData.password}
                onChange={e => setLoginData(prev => ({ ...prev, password: e.target.value }))}
                style={S.loginInput}
                placeholder="••••••••"
                required
              />
            </div>
            {loginError && <p style={S.loginError}>⚠️ {loginError}</p>}
            <button type="submit" style={{ ...S.loginBtn, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <Icon name="zap" size={16} color="white" />
              Start Learning
            </button>
          </form>

          <p style={S.cardNote}>New user? Trial is free for 3 months! 🎉</p>
        </div>
      </div>
    )
  }

  // ─── Profile Picker ───────────────────────────────────────────────
  if (showProfilePicker) {
    return (
      <div style={S.centeredContainer}>
        <div style={S.card}>
          <span style={{ ...S.logoEmoji, animation: 'none' }}>🐣</span>
          <h2 style={{ ...S.cardTitle, fontSize: '22px', marginBottom: '6px' }}>Who's learning today?</h2>
          <p style={{ ...S.cardSubtitle, marginBottom: '24px' }}>Choose a child profile to begin</p>
          {profiles.map(profile => (
            <button
              key={profile.id}
              onClick={() => handleProfileSelect(profile.id)}
              style={S.profileBtn}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#6EB4D4'
                e.currentTarget.style.background = '#EBF6FC'
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 6px 16px rgba(110,180,212,0.2)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#E8E8E8'
                e.currentTarget.style.background = 'white'
                e.currentTarget.style.transform = 'none'
                e.currentTarget.style.boxShadow = '0 2px 6px rgba(0,0,0,0.06)'
              }}
            >
              <span style={{ fontSize: '28px' }}>🐣</span>
              <div>
                <div style={{ fontWeight: 800, color: '#1E1E1E' }}>{profile.child_name}</div>
                {profile.age && <div style={{ fontSize: '12px', color: '#888', fontWeight: 600 }}>Age {profile.age}{profile.grade ? ` · ${profile.grade}` : ''}</div>}
              </div>
            </button>
          ))}
          <button
            onClick={handleLogout}
            style={{ ...S.logoutBtn, marginTop: '16px', width: '100%', justifyContent: 'center', padding: '8px', borderRadius: '10px' }}
          >
            <Icon name="x" size={13} color="#CC2929" />
            Log out
          </button>
        </div>
      </div>
    )
  }

  // ─── Chat Screen ──────────────────────────────────────────────────
  const activeProfile = profiles.find(p => p.id === selectedProfileId)

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="logo">🐦</div>
        <div>
          <h1>MamaBird & Chirpy</h1>
          <p>AI Educational Chatbot · Learning is as easy as pie! 🥧</p>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          {activeProfile && (
            <div style={S.profileChip}>
              <Icon name="user" size={11} color="#3A7030" />
              <span>{activeProfile.child_name}</span>
            </div>
          )}
          <div style={S.headerBtns}>
            {profiles.length > 1 && (
              <button onClick={() => setShowProfilePicker(true)} style={S.switchBtn}>
                Switch
              </button>
            )}
            {token && (
              <button
                onClick={() => setView('dashboard')}
                style={{ ...S.dashBtn, display: 'flex', alignItems: 'center', gap: '5px' }}
                onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.filter = 'brightness(1.08)' }}
                onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.filter = 'none' }}
              >
                <Icon name="bar-chart" size={12} color="white" />
                Dashboard
              </button>
            )}
            {token && currentUserRole === 'admin' && (
              <button
                onClick={() => setView('admin')}
                style={{ ...S.adminBtn, display: 'flex', alignItems: 'center', gap: '5px' }}
                onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.filter = 'brightness(1.08)' }}
                onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.filter = 'none' }}
              >
                <Icon name="shield" size={12} color="white" />
                Admin
              </button>
            )}
            {token && (
              <button
                onClick={handleLogout}
                style={S.logoutBtn}
                onMouseEnter={e => { e.currentTarget.style.background = '#FFF0F0'; e.currentTarget.style.borderColor = '#CC2929' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.borderColor = '#CC292933' }}
                title="Log out"
              >
                <Icon name="x" size={11} color="#CC2929" />
                Log out
              </button>
            )}
          </div>
        </div>
      </div>

      <CharacterSelector selected={character} onSelect={handleCharacterChange} />
      <SubjectSelector selected={subject} onSelect={setSubject} />

      <div className="messages-area">
        {messages.length === 0 && (
          <div className="welcome">
            <div className="big-emoji">🐦</div>
            <h2>Welcome to MamaBird & Chirpy!</h2>
            <p>
              Select a character above, choose a subject,<br />
              and start your learning adventure!<br /><br />
              <strong style={{ color: '#CC2929' }}>Tweet tweet! Learning is fun! ⭐</strong>
            </p>
          </div>
        )}

        {messages.map((msg, index) => (
          <ChatBubble key={index} message={msg} />
        ))}

        {isThinking && (
          <div className="thinking">
            <div className="bubble-avatar">
              {character === 'character_1' ? '🐦' : '🪺'}
            </div>
            <div>
              <div className="bubble-name">
                {character === 'character_1' ? 'Chirpy' : 'Mama Bird'}
              </div>
              <div className="thinking-dots">
                <span /><span /><span />
              </div>
              <div className="thinking-text" style={{ marginTop: '5px' }}>
                {character === 'character_1' ? 'Chirpy is thinking...' : 'Mama Bird is preparing...'}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input
          className="chat-input"
          placeholder={character === 'character_1' ? 'Type your answer here... 🐦' : 'Ask Mama Bird anything... 🪺'}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isThinking}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={isThinking || !input.trim()}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          Send
          <Icon name="send" size={14} color="white" />
        </button>
      </div>
    </div>
  )
}
