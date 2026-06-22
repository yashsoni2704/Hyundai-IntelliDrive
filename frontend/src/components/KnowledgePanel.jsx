export default function KnowledgePanel({ stats, loading, error, onClose }) {
  return (
    <div className="knowledge-panel">
      <div className="knowledge-panel-header">
        <h3>Knowledge Base</h3>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close panel">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      <div className="knowledge-panel-body">
        {loading && <p className="panel-muted">Loading stats...</p>}
        {error && <p className="panel-error">{error}</p>}
        {stats && !loading && (
          <dl className="stats-list">
            <div className="stat-item">
              <dt>Total FAQs Loaded</dt>
              <dd>{stats.total_faqs_loaded}</dd>
            </div>
            <div className="stat-item">
              <dt>Chroma Documents</dt>
              <dd>{stats.chroma_document_count}</dd>
            </div>
            <div className="stat-item">
              <dt>Embedding Model</dt>
              <dd>{stats.embedding_model}</dd>
            </div>
            <div className="stat-item">
              <dt>ChromaDB Status</dt>
              <dd>
                <span className={`status-badge status-badge--${stats.chroma_status}`}>
                  {stats.chroma_status}
                </span>
              </dd>
            </div>
            <div className="stat-item">
              <dt>Similarity Threshold</dt>
              <dd>{stats.similarity_threshold}</dd>
            </div>
          </dl>
        )}
      </div>
    </div>
  )
}
