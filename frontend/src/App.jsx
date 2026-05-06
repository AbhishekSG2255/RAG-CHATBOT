import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import ChatWindow from './components/ChatWindow'
import PersonaPanel from './components/PersonaPanel'
import TopicsPanel from './components/TopicsPanel'
import { getStatus, startProcessing } from './api/client'

const POLL_INTERVAL = 3000 // 3 seconds

function SetupScreen({ status, onStart }) {
  const isProcessing = status?.status === 'processing'
  const isError      = status?.status === 'error'
  const pct          = status?.progress_pct ?? 0

  return (
    <div className="setup-screen">
      <div className="setup-hero">
        <h1>Conversation Intelligence</h1>
        <p>
          Analyse thousands of real conversations using RAG. Discover topic patterns,
          extract user personas, and ask questions in natural language.
        </p>
      </div>

      <div className="setup-card">
        {isError ? (
          <>
            <h2>⚠️ Processing Error</h2>
            <p style={{ color: 'var(--pink)' }}>{status.error_message}</p>
            <button className="btn btn-primary" onClick={onStart} id="retry-btn">
              🔄 Retry Processing
            </button>
          </>
        ) : isProcessing ? (
          <>
            <h2>⚙️ Processing Conversations…</h2>
            <p>This runs once and takes a few minutes depending on your hardware.</p>
            <div className="progress-bar-wrap">
              <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
            </div>
            <div className="progress-label">
              <span className="step-label">{status.current_step || 'Starting…'}</span>
              <span>{pct.toFixed(0)}%</span>
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 16, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {status.total_messages > 0 && <span>📨 {status.total_messages.toLocaleString()} messages</span>}
              {status.total_topics > 0   && <span>🏷️ {status.total_topics.toLocaleString()} topics</span>}
              {status.total_checkpoints > 0 && <span>📋 {status.total_checkpoints.toLocaleString()} checkpoints</span>}
            </div>
          </>
        ) : (
          <>
            <h2>🚀 Start Processing</h2>
            <p>
              Parse and index all conversations from <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8em', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 4 }}>conversations.csv</code>.
              This runs once and saves everything locally.
            </p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={onStart} id="start-processing-btn">
                ⚡ Process Conversations
              </button>
            </div>
            <div style={{ marginTop: 12, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              ⏱️ Estimated time: 5–15 minutes on first run
            </div>
          </>
        )}
      </div>

      {/* Feature cards */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 800 }}>
        {[
          { icon: '🔍', title: 'RAG Retrieval', desc: 'Semantic + keyword hybrid search across all messages and topic summaries' },
          { icon: '🧠', title: 'User Persona', desc: 'Automatically extracts habits, personality, communication style from raw conversations' },
          { icon: '🗺️', title: 'Topic Detection', desc: 'TF-IDF cosine similarity detects topic shifts and creates auto-summaries' },
        ].map(f => (
          <div key={f.title} style={{
            background: 'var(--bg-glass)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)', padding: '1.25rem', flex: '1 1 200px', maxWidth: 240,
            backdropFilter: 'blur(12px)',
          }}>
            <div style={{ fontSize: '1.5rem', marginBottom: 8 }}>{f.icon}</div>
            <div style={{ fontWeight: 700, marginBottom: 6, fontSize: '0.95rem' }}>{f.title}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', lineHeight: 1.6 }}>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [activeTab,   setActiveTab]   = useState('chat')
  const [procStatus,  setProcStatus]  = useState(null)
  const [pollTimer,   setPollTimer]   = useState(null)

  const fetchStatus = async () => {
    try {
      const res = await getStatus()
      setProcStatus(res.data)
      return res.data
    } catch (e) {
      console.error('Status fetch error:', e)
      return null
    }
  }

  const startPolling = () => {
    const timer = setInterval(async () => {
      const s = await fetchStatus()
      if (s?.status === 'done' || s?.status === 'error') {
        clearInterval(timer)
        setPollTimer(null)
      }
    }, POLL_INTERVAL)
    setPollTimer(timer)
  }

  useEffect(() => {
    fetchStatus()
    return () => { if (pollTimer) clearInterval(pollTimer) }
  }, [])

  const handleStartProcessing = async () => {
    try {
      await startProcessing()
      await fetchStatus()
      startPolling()
    } catch (e) {
      console.error('Start error:', e)
    }
  }

  // Keep polling while processing
  useEffect(() => {
    if (procStatus?.status === 'processing' && !pollTimer) {
      startPolling()
    }
  }, [procStatus?.status])

  const isReady = procStatus?.status === 'done'

  return (
    <div className="app-wrapper">
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        processingStatus={procStatus}
      />
      <div className="main-content">
        {!isReady && procStatus?.status !== 'done' ? (
          <SetupScreen status={procStatus} onStart={handleStartProcessing} />
        ) : (
          <>
            {activeTab === 'chat'    && <ChatWindow    isReady={isReady} />}
            {activeTab === 'persona' && <PersonaPanel />}
            {activeTab === 'topics'  && <TopicsPanel  />}
          </>
        )}
      </div>
    </div>
  )
}
