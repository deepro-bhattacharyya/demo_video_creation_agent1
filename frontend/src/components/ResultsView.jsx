export default function ResultsView({ result, onReset }) {
  return (
    <div className="card results-card">
      <div className="success-icon">✓</div>
      <h2>Videos Ready</h2>
      <p className="results-sub">
        Both files have been validated and saved to the output directory.
      </p>

      <div className="output-list">
        <OutputFile
          label="Narrated Video"
          description="Full walkthrough with voice-over narration"
          path={result.narrated_video_path}
        />
        <OutputFile
          label="Silent Video"
          description="Condensed cut with captions, no audio"
          path={result.silent_video_path}
        />
      </div>

      <button className="btn-secondary" onClick={onReset}>
        Generate Another
      </button>
    </div>
  )
}

function OutputFile({ label, description, path }) {
  const filename = path ? path.replace(/\\/g, '/').split('/').pop() : '—'
  return (
    <div className="output-item">
      <div className="output-label">{label}</div>
      <div className="output-desc">{description}</div>
      <code className="output-path">{path ?? '—'}</code>
      <div className="output-filename">{filename}</div>
    </div>
  )
}
