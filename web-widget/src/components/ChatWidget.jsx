import { useState, useRef, useEffect } from 'react'
import CharacterSelector from './CharacterSelector'
import SubjectSelector from './SubjectSelector'
import ChatBubble from './ChatBubble'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

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
  const messagesEndRef = useRef(null)

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    try {
      const res = await axios.post(`${API_URL}/auth/login`, loginData)
      setToken(res.data.token)
      setShowLogin(false)
      // Add welcome message
      setMessages([{
        role: 'assistant',
        character: character,
        content: character === 'character_1'
          ? "Tweet tweet! 🐦 Hi there! I'm Chirpy! I'm so excited to learn with you today! What shall we practice? Pick a subject above and let's go! ⭐"
          : "Welcome! 🪺 I'm Mama Bird. I'm here to help with lesson plans, learning tips, and supporting your little one's education. How can I help you today? 💛"
      }])
    } catch (err) {
      setLoginError('Invalid email or password. Try: test@parent.com / Test1234!')
    }
  }

  const handleCharacterChange = (newCharacter) => {
    setCharacter(newCharacter)
    if (token) {
      setMessages([{
        role: 'assistant',
        character: newCharacter,
        content: newCharacter === 'character_1'
          ? "Tweet tweet! 🐦 Hi! I'm Chirpy! Ready to learn something amazing today? Pick a subject and let's fly! ⭐"
          : "Hello! 🪺 I'm Mama Bird. How can I support your child's learning journey today? 💛"
      }])
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isThinking) return

    const userMessage = {
      role: 'user',
      content: input.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsThinking(true)

    try {
      // For now (no API key yet) — use mock response
      // Replace this with real API call when Anthropic key arrives
      await new Promise(resolve => setTimeout(resolve, 1500))

      const mockResponses = {
        character_1: [
          `Tweet tweet! 🐦 Great question about ${subject}! Let me help you with that! Can you try spelling the word CAT? C-A-T! ⭐`,
          `Wow, you're doing amazing! 🌟 Let's try another one! What rhymes with BAT? Think think think... 🎉`,
          `Tweet tweet! 🐦 You're so smart! 5 eggs + 3 eggs = 8 eggs! Chirpy is SO proud of you! 🎊`,
        ],
        character_2: [
          `Hello! 🪺 For ${subject} at this level, I recommend starting with foundational concepts. Would you like me to generate a structured lesson plan? 💛`,
          `Wonderful question! 🌿 Here's what research tells us about teaching ${subject} effectively to young learners...`,
          `I can create a week-long lesson plan for ${subject}. Just let me know the grade level and I'll structure it day by day! 🪺`,
        ]
      }

      const responses = mockResponses[character]
      const randomResponse = responses[Math.floor(Math.random() * responses.length)]

      setMessages(prev => [...prev, {
        role: 'assistant',
        character: character,
        content: randomResponse
      }])

    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        character: character,
        content: "Oops! 🐦 Something went wrong. Please try again!"
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

  // ─── Login Screen ───────────────────────────────────────
  if (showLogin) {
    return (
      <div className="chat-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{
          background: 'white',
          borderRadius: '20px',
          padding: '40px',
          width: '100%',
          maxWidth: '400px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '60px', marginBottom: '10px' }}>🐦</div>
          <h1 style={{ color: '#CC2929', marginBottom: '5px' }}>MamaBird & Chirpy</h1>
          <p style={{ color: '#888', marginBottom: '30px', fontSize: '14px' }}>
            AI Educational Chatbot
          </p>

          <form onSubmit={handleLogin}>
            <input
              type="email"
              placeholder="Email address"
              value={loginData.email}
              onChange={e => setLoginData(prev => ({ ...prev, email: e.target.value }))}
              className="chat-input"
              style={{ width: '100%', marginBottom: '12px', borderRadius: '10px' }}
              required
            />
            <input
              type="password"
              placeholder="Password"
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

  // ─── Chat Screen ────────────────────────────────────────
  return (
    <div className="chat-container">

      {/* Header */}
      <div className="chat-header">
        <div className="logo">🐦</div>
        <div>
          <h1>MamaBird & Chirpy</h1>
          <p>AI Educational Chatbot • Learning is as easy as pie! 🥧</p>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: '12px', color: '#4A8B3F', fontWeight: 600 }}>
          ✅ Trial Active
        </div>
      </div>

      {/* Character Selector */}
      <CharacterSelector selected={character} onSelect={handleCharacterChange} />

      {/* Subject Selector */}
      <SubjectSelector selected={subject} onSelect={setSubject} />

      {/* Messages */}
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

      {/* Input */}
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