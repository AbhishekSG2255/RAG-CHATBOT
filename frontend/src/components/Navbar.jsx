export default function Navbar({ activeTab, onTabChange, processingStatus }) {
  const tabs = [
    { id: 'chat',        label: 'Chat',        icon: '💬' },
    { id: 'persona',     label: 'Persona',     icon: '🧠' },
    { id: 'topics',      label: 'Topics',      icon: '🗺️' },
    { id: 'checkpoints', label: 'Checkpoints', icon: '📋' },
  ]

  const dotClass = processingStatus?.status === 'done'
    ? 'done' : processingStatus?.status === 'processing'
    ? 'processing' : processingStatus?.status === 'error'
    ? 'error' : ''

  const statusLabel = processingStatus?.status === 'done'
    ? `${processingStatus.total_messages?.toLocaleString()} msgs ready`
    : processingStatus?.status === 'processing'
    ? `Processing… ${processingStatus.progress_pct?.toFixed(0)}%`
    : processingStatus?.status === 'error'
    ? 'Error'
    : 'Not processed'

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="logo-icon">🤖</div>
        <span>RAG Chatbot</span>
      </div>

      <div className="navbar-tabs">
        {tabs.map(t => (
          <button
            key={t.id}
            className={`nav-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => onTabChange(t.id)}
            id={`nav-tab-${t.id}`}
          >
            <span>{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      <div className="navbar-status">
        <span className={`status-dot ${dotClass}`} />
        <span>{statusLabel}</span>
      </div>
    </nav>
  )
}
