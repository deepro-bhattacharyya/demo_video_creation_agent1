import { useState } from 'react'

export default function PipelineForm({ onSubmit }) {
  const [agentId, setAgentId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [customInstructions, setCustomInstructions] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!agentId.trim() || !projectId.trim()) return
    setLoading(true)
    await onSubmit({
      agentId: agentId.trim(),
      projectId: projectId.trim(),
      customInstructions,
    })
    // parent will change view; no need to reset loading
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Generate Demo Video</h2>

      <div className="form-group">
        <label>Agent ID</label>
        <input
          type="text"
          placeholder="e.g. defect-triaging-crewai"
          value={agentId}
          onChange={e => setAgentId(e.target.value)}
          required
          autoFocus
        />
      </div>

      <div className="form-group">
        <label>Project ID</label>
        <input
          type="text"
          placeholder="Your project ID on the platform"
          value={projectId}
          onChange={e => setProjectId(e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label>
          Custom Instructions&nbsp;
          <span className="label-hint">(optional)</span>
        </label>
        <textarea
          placeholder="Specific tone, naming conventions, focus areas…"
          value={customInstructions}
          onChange={e => setCustomInstructions(e.target.value)}
          rows={3}
        />
      </div>

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Starting…' : 'Start Pipeline'}
      </button>
    </form>
  )
}
