import { useState, useRef, useEffect } from 'react'
import CharacterSelector from './CharacterSelector'
import SubjectSelector from './SubjectSelector'
import ChatBubble from './ChatBubble'
import PaywallScreen from './PaywallScreen'
import ParentDashboard from './ParentDashboard'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
  const [view, setView] = useState('chat') // 'chat' | 'dashboard' | 'paywall'
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
      setToken(tok)

      // Fetch child profiles
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
      const profile = profiles.find(p => p.id === selectedProfileId)
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
        role: 'assistant',
        character: character,
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
        {
          child_profile_id: selectedProfileId,
          character: character,
          subject: subject,
          message: userMessage.content
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      )

      const newBadges = res.data.new_badges || []
      setMessages(prev => [...prev, {
        role: 'assistant',
        character: character,
        content: res.data.response,
        progress: res.data.progress,
        illustration: res.data.illustration_key,
        newBadges,
      }])
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 402) {
        const code = typeof detail === 'object' ? detail.code : 'SUBSCRIPTION_REQUIRED'
        setPaywallErrorCode(code)
        setView('paywall')
        return
      }
      const errorMsg = typeof detail === 'object' ? detail.message : (detail || "Tweet tweet! 🐦 Something went wrong. Please try again!")
      setMessages(prev => [...prev, {
        role: 'assistant',
        character: character,
        content: typeof errorMsg === 'string' ? errorMsg : "Something went wrong. Please try again!"
      }])
    } finally {
      setIsThinking(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ─── Paywall Screen ──────────────────────────────────────────────
  if (view === 'paywall') {
    return (
      <PaywallScreen
        token={token}
        errorCode={paywallErrorCode}
        onBack={() => setView('chat')}
      />
    )
  }

  // ─── Dashboard Screen ─────────────────────────────────────────────
  if (view === 'dashboard') {
    return (
      <ParentDashboard
        token={token}
        selectedProfileId={selectedProfileId}
        onBack={() => setView('chat')}
      />
    )
  }

  // ─── Login Screen ────────────────────────────────────────────────
  if (showLogin) {
    return (
      <div className="chat-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{
          background: 'white', borderRadius: '20px', padding: '40px',
          width: '100%', maxWidth: '400px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.1)', textAlign: 'center'
        }}>
          <div style={{ fontSize: '60px', marginBottom: '10px' }}>🐦</div>
          <h1 style={{ color: '#CC2929', marginBottom: '5px' }}>MamaBird & Chirpy</h1>
          <p style={{ color: '#888', marginBottom: '30px', fontSize: '14px' }}>AI Educational Chatbot</p>

          <form onSubmit={handleLogin}>
            <input
              type="email" placeholder="Email address"
              value={loginData.email}
              onChange={e => setLoginData(prev => ({ ...prev, email: e.target.value }))}
              className="chat-input"
              style={{ width: '100%', marginBottom: '12px', borderRadius: '10px' }}
              required
            />
            <input
              type="password" placeholder="Password"
              value={loginData.password}
              onChange={e => setLoginData(prev => ({ ...prev, password: e.target.value }))}
              className="chat-input"
              style={{ width: '100%', marginBottom: '20px', borderRadius: '10px' }}
              required
            />
            {loginError && (
              <p style={{ color: '#CC2929', fontSize: '13px', marginBottom: '15px' }}>
                {loginError}
              </p>
            )}
            <button type="submit" className="send-btn" style={{ width: '100%', borderRadius: '10px' }}>
              Start Learning! 🚀
            </button>
          </form>

          <p style={{ marginTop: '20px', fontSize: '12px', color: '#aaa' }}>
            New user? The trial is free for 3 months! 🎉
          </p>
        </div>
      </div>
    )
  }

  // ─── Profile Picker ──────────────────────────────────────────────
  if (showProfilePicker) {
    return (
      <div className="chat-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{
          background: 'white', borderRadius: '20px', padding: '40px',
          width: '100%', maxWidth: '400px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.1)', textAlign: 'center'
        }}>
          <div style={{ fontSize: '50px', marginBottom: '10px' }}>🐣</div>
          <h2 style={{ color: '#CC2929', marginBottom: '20px' }}>Who is learning today?</h2>
          {profiles.map(profile => (
            <button
              key={profile.id}
              onClick={() => handleProfileSelect(profile.id)}
              className="send-btn"
              style={{ width: '100%', marginBottom: '10px', borderRadius: '10px', fontSize: '16px' }}
            >
              {profile.child_name} {profile.age ? `(age ${profile.age})` : ''}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // ─── Chat Screen ─────────────────────────────────────────────────
  const activeProfile = profiles.find(p => p.id === selectedProfileId)

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="logo">🐦</div>
        <div>
          <h1>MamaBird & Chirpy</h1>
          <p>AI Educational Chatbot • Learning is as easy as pie! 🥧</p>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          {activeProfile && (
            <div style={{ fontSize: '13px', color: '#4A8B3F', fontWeight: 600 }}>
              👤 {activeProfile.child_name}
            </div>
          )}
          <div style={{ display: 'flex', gap: '6px', marginTop: '4px', justifyContent: 'flex-end' }}>
            {profiles.length > 1 && (
              <button
                onClick={() => setShowProfilePicker(true)}
                style={{ fontSize: '11px', color: '#888', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                Switch child
              </button>
            )}
            {token && (
              <button
                onClick={() => setView('dashboard')}
                style={{
                  fontSize: '11px', color: 'white', background: '#4A8B3F',
                  border: 'none', borderRadius: '6px', padding: '3px 8px', cursor: 'pointer',
                }}
              >
                📊 Dashboard
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
            <p>Select a character above, choose a subject,<br />
            and start your learning adventure!<br /><br />
            <strong>Tweet tweet! Learning is fun! ⭐</strong></p>
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
              <div className="thinking-text" style={{ marginTop: '4px' }}>
                {character === 'character_1'
                  ? 'Chirpy is thinking... 🐦'
                  : 'Mama Bird is preparing... 🪺'}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input
          className="chat-input"
          placeholder={
            character === 'character_1'
              ? "Type your answer here... 🐦"
              : "Ask Mama Bird anything... 🪺"
          }
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isThinking}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={isThinking || !input.trim()}
        >
          Send 🚀
        </button>
      </div>
    </div>
  )
}
