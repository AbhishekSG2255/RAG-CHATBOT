import { useEffect, useState } from 'react'
import { getPersona } from '../api/client'

function TagList({ items, color }) {
  if (!items?.length) return <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>None detected</span>
  return (
    <div className="tag-list">
      {items.map((item, i) => (
        <span key={i} className={`tag ${color}`}>{item}</span>
      ))}
    </div>
  )
}

function FactRows({ obj }) {
  if (!obj || !Object.keys(obj).length)
    return <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No data</span>

  return Object.entries(obj).map(([key, val]) => {
    const display = Array.isArray(val) ? val.join(', ') : String(val)
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    return (
      <div className="fact-row" key={key}>
        <span className="fact-key">{label}</span>
        <span className="fact-value">{display}</span>
      </div>
    )
  })
}

export default function PersonaPanel() {
  const [personaData, setPersonaData] = useState(null)
  const [selectedSpeaker, setSelectedSpeaker] = useState('User 1')
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  useEffect(() => {
    getPersona()
      .then(res => setPersonaData(res.data))
      .catch(err => setError(err.response?.data?.error || 'Failed to load persona'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="panel-layout">
      <div className="empty-state">
        <div className="spinner" />
        <h3>Loading persona data…</h3>
      </div>
    </div>
  )

  if (error) return (
    <div className="panel-layout">
      <div className="empty-state">
        <div className="big-icon">⚠️</div>
        <h3>{error}</h3>
        <p>Make sure you've run the data processing step first.</p>
      </div>
    </div>
  )

  // Handle old structure vs new per-speaker structure
  const isMultiSpeaker = personaData && ('User 1' in personaData || 'User 2' in personaData)
  const persona = isMultiSpeaker ? (personaData[selectedSpeaker] || {}) : (personaData || {})

  const facts = persona?.personal_facts || {}
  const personality = persona?.personality || {}
  const style = persona?.communication_style || {}
  const habits = persona?.habits || []

  return (
    <div className="panel-layout">
      <div className="panel-header">
        <h2>🧠 User Persona</h2>
        <p>Extracted from {persona?.total_messages_analyzed?.toLocaleString() || '?'} messages using pattern analysis</p>
      </div>

      {isMultiSpeaker && (
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <button 
            className={`btn ${selectedSpeaker === 'User 1' ? 'btn-primary' : 'btn-ghost'}`} 
            onClick={() => setSelectedSpeaker('User 1')}
          >
            User 1
          </button>
          <button 
            className={`btn ${selectedSpeaker === 'User 2' ? 'btn-primary' : 'btn-ghost'}`} 
            onClick={() => setSelectedSpeaker('User 2')}
          >
            User 2
          </button>
        </div>
      )}

      {persona?.summary && (
        <div className="summary-box">{persona.summary}</div>
      )}

      <div className="persona-grid">
        {/* Habits */}
        <div className="persona-card" id="persona-habits">
          <div className="persona-card-header">
            <span className="card-icon">🌿</span>
            <div>
              <div className="card-title">Habits & Routines</div>
              <div className="card-subtitle">Detected lifestyle patterns</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {habits.length
              ? habits.map((h, i) => (
                  <div key={i} style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: 12, borderLeft: '2px solid rgba(20,184,166,0.4)' }}>
                    {h}
                  </div>
                ))
              : <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>None detected</span>
            }
          </div>
        </div>

        {/* Hobbies & Interests */}
        <div className="persona-card" id="persona-hobbies">
          <div className="persona-card-header">
            <span className="card-icon">🎯</span>
            <div>
              <div className="card-title">Interests & Hobbies</div>
              <div className="card-subtitle">Frequently mentioned activities</div>
            </div>
          </div>
          <TagList items={facts.hobbies} color="teal" />
        </div>

        {/* Personality */}
        <div className="persona-card" id="persona-personality">
          <div className="persona-card-header">
            <span className="card-icon">✨</span>
            <div>
              <div className="card-title">Personality Traits</div>
              <div className="card-subtitle">Inferred from language patterns</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 12 }}>
            <TagList items={personality.key_traits} color="purple" />
          </div>
          <FactRows obj={{
            ...(personality.overall_tone && { 'Overall Tone': personality.overall_tone }),
            ...(personality.humor && { 'Humor': personality.humor }),
            ...(personality.empathy && { 'Empathy': personality.empathy }),
            ...(personality.curiosity && { 'Curiosity': personality.curiosity }),
            ...(personality.enthusiasm && { 'Enthusiasm': personality.enthusiasm }),
          }} />
        </div>

        {/* Communication Style */}
        <div className="persona-card" id="persona-comms">
          <div className="persona-card-header">
            <span className="card-icon">💬</span>
            <div>
              <div className="card-title">Communication Style</div>
              <div className="card-subtitle">How they write and express themselves</div>
            </div>
          </div>
          <FactRows obj={{
            ...(style.message_length && { 'Message Length': style.message_length }),
            ...(style.avg_words_per_message && { 'Avg Words/Msg': style.avg_words_per_message }),
            ...(style.formality && { 'Formality': style.formality }),
            ...(style.emoji_usage && { 'Emoji Usage': style.emoji_usage }),
            ...(style.exclamation_usage && { 'Exclamation Use': style.exclamation_usage }),
            ...(style.question_asking && { 'Question Asking': style.question_asking }),
          }} />
          {style.common_phrases?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>Common phrases</div>
              <TagList items={style.common_phrases} color="amber" />
            </div>
          )}
        </div>

        {/* Personal Facts */}
        <div className="persona-card" id="persona-facts">
          <div className="persona-card-header">
            <span className="card-icon">📋</span>
            <div>
              <div className="card-title">Personal Facts</div>
              <div className="card-subtitle">Occupations, relationships, pets</div>
            </div>
          </div>
          {facts.likely_occupations?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>Likely Occupations</div>
              <TagList items={facts.likely_occupations} color="pink" />
            </div>
          )}
          <FactRows obj={{
            ...(facts.pets?.length && { 'Pets': facts.pets.join(', ') }),
            ...(facts.family_relationships?.length && { 'Family': facts.family_relationships.join(', ') }),
          }} />
        </div>

        {/* Locations */}
        {facts.mentioned_locations?.length > 0 && (
          <div className="persona-card" id="persona-locations">
            <div className="persona-card-header">
              <span className="card-icon">📍</span>
              <div>
                <div className="card-title">Mentioned Locations</div>
                <div className="card-subtitle">Places referenced in conversations</div>
              </div>
            </div>
            <TagList items={facts.mentioned_locations} color="amber" />
          </div>
        )}

        {/* Books */}
        {facts.mentioned_books_authors?.length > 0 && (
          <div className="persona-card" id="persona-books">
            <div className="persona-card-header">
              <span className="card-icon">📚</span>
              <div>
                <div className="card-title">Books & Authors</div>
                <div className="card-subtitle">Mentioned in conversations</div>
              </div>
            </div>
            <TagList items={facts.mentioned_books_authors} color="teal" />
          </div>
        )}
      </div>
    </div>
  )
}
