import { useState, useRef, useEffect } from 'react'
import { sendChat } from '../api/client'

const SUGGESTIONS = [
  'What kind of person is this user?',
  'What are their habits?',
  'How do they talk?',
  'What are their hobbies?',
  'What jobs do they mention?',
  'Do they have pets?',
]

function TypingIndicator() {
  return (
    <div className="message-row bot">
      <div className="avatar bot">🤖</div>
      <div className="bubble bot">
        <div className="typing-indicator">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const text = msg.content || ''
  const [expandedSources, setExpandedSources] = useState(false)

  // Convert **bold** markdown to <strong>
  const formatted = text
    .split('\n')
    .map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/)
      return (
        <span key={i}>
          {parts.map((p, j) =>
            p.startsWith('**') && p.endsWith('**')
              ? <strong key={j}>{p.slice(2, -2)}</strong>
              : p
          )}
          {i < text.split('\n').length - 1 && <br />}
        </span>
      )
    })

  const sources = msg.sources
  const hasSemanticSources = sources?.semantic_chunks?.length > 0
  const hasTopicSources = sources?.topic_summaries?.length > 0
  
  const modeBadge = msg.answer_mode === 'groq' ? '✨ AI' : msg.answer_mode === 'persona' ? '🧠 Persona' : '📝 Extractive'

  return (
    <div className={`message-row ${isUser ? 'user' : 'bot'}`}>
      <div className={`avatar ${isUser ? 'user' : 'bot'}`}>
        {isUser ? '👤' : '🤖'}
      </div>
      <div className={`bubble ${isUser ? 'user' : 'bot'}`}>
        {!isUser && msg.answer_mode && (
           <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', textAlign: 'right' }}>
             {modeBadge}
           </div>
        )}
        {formatted}
        {!isUser && (hasSemanticSources || hasTopicSources) && (
          <div className="bubble-sources" onClick={() => setExpandedSources(!expandedSources)} style={{ cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
              <span style={{ marginRight: 6 }}>Sources {expandedSources ? '▼' : '▶'}:</span>
              {hasTopicSources && sources.topic_summaries.map((t, i) => (
                <span key={`t-${i}`} className="source-tag">Topic {t.topic_number}</span>
              ))}
              {hasSemanticSources && (
                <span className="source-tag">
                  {sources.semantic_chunks.length} message chunk{sources.semantic_chunks.length > 1 ? 's' : ''}
                </span>
              )}
            </div>
            
            {expandedSources && (
              <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {hasTopicSources && sources.topic_summaries.map((t, i) => (
                  <div key={`ts-${i}`} style={{ background: 'rgba(0,0,0,0.1)', padding: '8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                    <strong>Topic {t.topic_number} (msgs {t.start_global_index}-{t.end_global_index}):</strong><br/>
                    {t.summary}
                  </div>
                ))}
                {hasSemanticSources && sources.semantic_chunks.map((c, i) => (
                  <div key={`cs-${i}`} style={{ background: 'rgba(0,0,0,0.1)', padding: '8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                    <strong>Messages {c.start_global}-{c.end_global}:</strong><br/>
                    {c.preview}...
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatWindow({ isReady }) {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('chatHistory')
    return saved ? JSON.parse(saved) : []
  })
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('chatHistory', JSON.stringify(messages))
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (text) => {
    const query = (text || input).trim()
    if (!query || loading) return

    const userMsg = { role: 'user', content: query, id: Date.now() }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await sendChat(query, newMessages.slice(0, -1)) // Pass history without current query
      const botMsg = {
        role: 'bot',
        content: res.data.answer,
        answer_mode: res.data.answer_mode,
        sources: res.data.sources,
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      const errMsg = {
        role: 'bot',
        content: err.response?.data?.error || 'Something went wrong. Please try again.',
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearHistory = () => {
    if (window.confirm("Clear chat history?")) {
      setMessages([])
      localStorage.removeItem('chatHistory')
    }
  }

  return (
    <div className="chat-layout">
      {messages.length > 0 && (
        <button onClick={clearHistory} style={{ position: 'absolute', top: 10, right: 10, zIndex: 10, background: 'var(--bg-glass)', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px 8px' }}>
          Clear History
        </button>
      )}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">💬</div>
            <h3>Ask me anything about the conversations</h3>
            <p>I'll search through thousands of messages and topic summaries to answer your question.</p>
            <div className="suggestion-chips">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  className="chip"
                  onClick={() => sendMessage(s)}
                  disabled={!isReady || loading}
                  id={`suggestion-${s.replace(/\s+/g,'-').toLowerCase().slice(0,30)}`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)
        )}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder={isReady ? 'Ask about habits, personality, topics…' : 'Processing data first…'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isReady || loading}
            rows={1}
            id="chat-input"
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={!isReady || loading || !input.trim()}
            id="send-btn"
            title="Send message"
          >
            {loading ? '⏳' : '➤'}
          </button>
        </div>
      </div>
    </div>
  )
}
