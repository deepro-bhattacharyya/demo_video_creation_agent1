const STEPS = [
  {
    label: 'Fetching agent spec',
    hint: 'Reading agent documentation from the platform',
  },
  {
    label: 'Recording run',
    hint: 'Logging in and running the agent via Playwright (~5 min)',
  },
  {
    label: 'Generating script',
    hint: 'Gemini is writing the timed narration scene list',
  },
  {
    label: 'Awaiting your review',
    hint: 'Script ready — review step coming up next',
  },
]

export default function ProgressView() {
  return (
    <div className="card progress-card">
      <div className="spinner" />
      <h2>Pipeline Running</h2>
      <p className="progress-note">
        Running in the background — this typically takes{' '}
        <strong>5–10 minutes</strong>. This page polls every 5 seconds.
      </p>

      <ul className="steps-list">
        {STEPS.map((step, i) => (
          <li key={i} className="step-item">
            <span className="step-dot" />
            <div>
              <div className="step-label">{step.label}</div>
              <div className="step-hint">{step.hint}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
