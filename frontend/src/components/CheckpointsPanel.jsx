import { useEffect, useState, useCallback } from 'react'
import { getCheckpoints, getStats } from '../api/client'

export default function CheckpointsPanel() {
  const [checkpoints, setCheckpoints] = useState([])
  const [page,      setPage]      = useState(1)
  const [totalPages,setTotalPages]= useState(1)
  const [count,     setCount]     = useState(0)
  const [loading,   setLoading]   = useState(true)
  const [stats,     setStats]     = useState(null)

  const loadCheckpoints = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getCheckpoints(page)
      setCheckpoints(res.data.results)
      setTotalPages(res.data.total_pages)
      setCount(res.data.count)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { loadCheckpoints() }, [loadCheckpoints])

  useEffect(() => {
    getStats().then(r => setStats(r.data)).catch(() => {})
  }, [])

  return (
    <div className="panel-layout">
      <div className="panel-header">
        <h2>📋 100-Message Checkpoints</h2>
        <p>Independent summaries generated every 100 messages chronologically.</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-pill">
            <span className="stat-num">{stats.counts?.messages?.toLocaleString()}</span>
            <span className="stat-lbl">Total Messages</span>
          </div>
          <div className="stat-pill">
            <span className="stat-num">{stats.counts?.checkpoints?.toLocaleString()}</span>
            <span className="stat-lbl">100-Msg Checkpoints</span>
          </div>
        </div>
      )}

      {loading ? (
        <div className="empty-state">
          <div className="spinner" />
          <h3>Loading checkpoints…</h3>
        </div>
      ) : checkpoints.length === 0 ? (
        <div className="empty-state">
          <div className="big-icon">📋</div>
          <h3>No checkpoints yet</h3>
          <p>Run data processing first.</p>
        </div>
      ) : (
        <>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Showing {checkpoints.length} of {count.toLocaleString()} checkpoints
          </div>

          <div className="topic-timeline" id="checkpoints-list">
            {checkpoints.map((cp, idx) => {
              return (
                <div className="topic-item" key={cp.checkpoint_id} id={`checkpoint-${cp.checkpoint_id}`}>
                  <div className="topic-marker">
                    <div className="topic-dot" style={{ backgroundColor: 'var(--amber)' }} />
                    {idx < checkpoints.length - 1 && <div className="topic-line" />}
                  </div>
                  <div className="topic-body">
                    <div className="topic-meta">
                      <span className="topic-number">Checkpoint #{cp.checkpoint_number}</span>
                      <span className="topic-range">
                        msgs {cp.start_global_index} – {cp.end_global_index}
                      </span>
                    </div>
                    <div className="topic-summary">{cp.summary || 'No summary available.'}</div>
                  </div>
                </div>
              )
            })}
          </div>

          {totalPages > 1 && (
            <div className="pagination" id="checkpoints-pagination">
              <button
                className="page-btn"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >← Prev</button>
              <span className="page-info">Page {page} of {totalPages}</span>
              <button
                className="page-btn"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
