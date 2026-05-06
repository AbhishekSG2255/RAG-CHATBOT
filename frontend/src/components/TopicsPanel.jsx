import { useEffect, useState, useCallback } from 'react'
import { getTopics, getStats } from '../api/client'

export default function TopicsPanel() {
  const [topics,    setTopics]    = useState([])
  const [page,      setPage]      = useState(1)
  const [totalPages,setTotalPages]= useState(1)
  const [count,     setCount]     = useState(0)
  const [search,    setSearch]    = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [loading,   setLoading]   = useState(true)
  const [stats,     setStats]     = useState(null)

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [search])

  const loadTopics = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getTopics(page, debouncedSearch)
      setTopics(res.data.results)
      setTotalPages(res.data.total_pages)
      setCount(res.data.count)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [page, debouncedSearch])

  useEffect(() => { loadTopics() }, [loadTopics])

  useEffect(() => {
    getStats().then(r => setStats(r.data)).catch(() => {})
  }, [])

  const parseKeywords = (kw) => {
    if (Array.isArray(kw)) return kw
    try { return JSON.parse(kw) } catch { return [] }
  }

  return (
    <div className="panel-layout">
      <div className="panel-header">
        <h2>🗺️ Topic Checkpoints</h2>
        <p>Topics detected by TF-IDF cosine similarity — every topic shift creates a new checkpoint</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-pill">
            <span className="stat-num">{stats.counts?.messages?.toLocaleString()}</span>
            <span className="stat-lbl">Total Messages</span>
          </div>
          <div className="stat-pill">
            <span className="stat-num">{stats.counts?.topics?.toLocaleString()}</span>
            <span className="stat-lbl">Topic Checkpoints</span>
          </div>
          <div className="stat-pill">
            <span className="stat-num">{stats.counts?.checkpoints?.toLocaleString()}</span>
            <span className="stat-lbl">100-Msg Checkpoints</span>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="search-bar" id="topics-search">
        <input
          className="search-input"
          placeholder="Search topics by keyword or summary…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          id="topics-search-input"
        />
        {search && (
          <button className="btn btn-ghost" onClick={() => setSearch('')} style={{ padding: '8px 14px' }}>✕</button>
        )}
      </div>

      {loading ? (
        <div className="empty-state">
          <div className="spinner" />
          <h3>Loading topics…</h3>
        </div>
      ) : topics.length === 0 ? (
        <div className="empty-state">
          <div className="big-icon">🔍</div>
          <h3>{search ? 'No topics match your search' : 'No topics yet'}</h3>
          <p>{search ? 'Try a different keyword.' : 'Run data processing first.'}</p>
        </div>
      ) : (
        <>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Showing {topics.length} of {count.toLocaleString()} topics
          </div>

          <div className="topic-timeline" id="topics-list">
            {topics.map((topic, idx) => {
              const keywords = parseKeywords(topic.keywords)
              return (
                <div className="topic-item" key={topic.topic_id} id={`topic-${topic.topic_id}`}>
                  <div className="topic-marker">
                    <div className="topic-dot" />
                    {idx < topics.length - 1 && <div className="topic-line" />}
                  </div>
                  <div className="topic-body">
                    <div className="topic-meta">
                      <span className="topic-number">Topic {topic.topic_number}</span>
                      <span className="topic-range">
                        msgs {topic.start_global_index} – {topic.end_global_index}
                        &nbsp;({topic.end_global_index - topic.start_global_index + 1} messages)
                      </span>
                    </div>
                    <div className="topic-summary">{topic.summary || 'No summary available.'}</div>
                    {keywords.length > 0 && (
                      <div className="topic-keywords">
                        {keywords.map((kw, i) => (
                          <span key={i} className="keyword-badge">{kw}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {totalPages > 1 && (
            <div className="pagination" id="topics-pagination">
              <button
                className="page-btn"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                id="topics-prev"
              >← Prev</button>
              <span className="page-info">Page {page} of {totalPages}</span>
              <button
                className="page-btn"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                id="topics-next"
              >Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
