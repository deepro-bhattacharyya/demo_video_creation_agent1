import { useState } from 'react'

export default function SceneReviewer({ scenes, customInstructions, onResume }) {
  const [edited, setEdited] = useState(() => scenes.map(s => ({ ...s })))
  const [submitting, setSubmitting] = useState(false)

  const update = (index, field, value) =>
    setEdited(prev => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)))

  const handle = async (action) => {
    setSubmitting(true)
    await onResume(action, action === 'edit' ? edited : [])
    // parent transitions to 'running'; submitting stays true
  }

  return (
    <div className="reviewer">
      {/* Header */}
      <div className="reviewer-header card">
        <h2>Review Narration Script</h2>
        <p className="reviewer-sub">
          {scenes.length} scene{scenes.length !== 1 ? 's' : ''} generated.&nbsp;
          Edit any field then click <em>Submit Edits</em>, or click{' '}
          <em>Approve &amp; Render</em> to proceed as-is.
        </p>
        {customInstructions && (
          <div className="instructions-banner">
            <strong>Custom instructions:</strong> {customInstructions}
          </div>
        )}
      </div>

      {/* Scene list */}
      <div className="scenes-list">
        {edited.map((scene, i) => (
          <div key={i} className="scene-card">
            <div className="scene-timing">
              Scene {i + 1}&nbsp;&nbsp;·&nbsp;&nbsp;
              {scene.start}s – {scene.end}s
            </div>
            <div className="scene-fields">
              <div className="field-group">
                <label>On Screen</label>
                <input
                  value={scene.on_screen}
                  onChange={e => update(i, 'on_screen', e.target.value)}
                  placeholder="Short caption (max 10 words)"
                />
              </div>
              <div className="field-group">
                <label>Narration</label>
                <textarea
                  value={scene.narration}
                  onChange={e => update(i, 'narration', e.target.value)}
                  rows={3}
                  placeholder="Narrator line read aloud"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sticky action bar */}
      <div className="reviewer-actions">
        <button
          className="btn-secondary"
          onClick={() => handle('edit')}
          disabled={submitting}
        >
          Submit Edits
        </button>
        <button
          className="btn-primary"
          onClick={() => handle('approve')}
          disabled={submitting}
        >
          Approve &amp; Render
        </button>
      </div>
    </div>
  )
}
