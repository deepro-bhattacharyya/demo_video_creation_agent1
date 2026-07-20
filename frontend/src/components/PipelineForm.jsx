import { useState } from 'react'

export default function PipelineForm({ onSubmit }) {
  const [sourceType, setSourceType]             = useState('hub')
  const [agentName, setAgentName]               = useState('')
  const [projectName, setProjectName]           = useState('')
  const [agentFolder, setAgentFolder]           = useState('')
  const [customInstructions, setCustomInstructions] = useState('')
  const [loading, setLoading]                   = useState(false)

  const isHub        = sourceType === 'hub'
  const hubValid     = agentName.trim() && projectName.trim()
  const standaloneValid = agentFolder.trim()
  const canSubmit    = isHub ? hubValid : standaloneValid

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    await onSubmit({
      sourceType,
      agentName:   agentName.trim(),
      projectName: projectName.trim(),
      agentFolder: agentFolder.trim(),
      customInstructions,
    })
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Generate Demo Video</h2>

      {/* Source type toggle */}
      <div className="form-group">
        <label>Source</label>
        <div className="source-toggle">
          <label className={`toggle-option ${isHub ? 'active' : ''}`}>
            <input
              type="radio"
              name="sourceType"
              value="hub"
              checked={isHub}
              onChange={() => setSourceType('hub')}
            />
            Platform (Hub)
          </label>
          <label className={`toggle-option ${!isHub ? 'active' : ''}`}>
            <input
              type="radio"
              name="sourceType"
              value="standalone"
              checked={!isHub}
              onChange={() => setSourceType('standalone')}
            />
            Standalone Folder
          </label>
        </div>
      </div>

      {/* Hub fields */}
      {isHub && (
        <>
          <div className="form-group">
            <label>Project Name</label>
            <input
              type="text"
              placeholder="e.g. Dev test project"
              value={projectName}
              onChange={e => setProjectName(e.target.value)}
              required={isHub}
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Agent Name</label>
            <input
              type="text"
              placeholder="e.g. Defect Triage (CrewAI)"
              value={agentName}
              onChange={e => setAgentName(e.target.value)}
              required={isHub}
            />
          </div>
        </>
      )}

      {/* Standalone field */}
      {!isHub && (
        <div className="form-group">
          <label>Agent Folder Path</label>
          <input
            type="text"
            placeholder="e.g. C:\Projects\my-agent"
            value={agentFolder}
            onChange={e => setAgentFolder(e.target.value)}
            required={!isHub}
            autoFocus
          />
          <span className="label-hint">
            Folder must contain a <code>demo_config.yaml</code> file.
          </span>
        </div>
      )}

      {/* Custom instructions (both modes) */}
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

      <button type="submit" className="btn-primary" disabled={loading || !canSubmit}>
        {loading ? 'Starting…' : 'Start Pipeline'}
      </button>
    </form>
  )
}
