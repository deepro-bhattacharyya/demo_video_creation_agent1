const STEPS = [
  { key: 'select_agent',     label: 'Fetching agent spec',      hint: 'Reading agent name and spec from the platform' },
  { key: 'capture_run',      label: 'Recording run',            hint: 'Running the agent and screen-recording (~5 min)' },
  { key: 'generate_script',  label: 'Generating script',        hint: 'Gemini writes the timed narration scenes' },
  { key: 'review_script',    label: 'Awaiting your review',     hint: 'Script ready — review step coming up next' },
  { key: 'synthesize_audio', label: 'Synthesising voice-over',  hint: 'Edge TTS converts narration lines to audio' },
  { key: 'assemble_full',    label: 'Assembling narrated cut',  hint: 'Merging screen recording with audio track' },
  { key: 'assemble_silent',  label: 'Assembling silent cut',    hint: 'Burning captions onto the video' },
  { key: 'finalize',         label: 'Finalising',               hint: 'Validating output files and cleaning up' },
]

export default function ProgressView({ completedSteps = [], currentNode = null }) {
  return (
    <div className="card progress-card">
      <div className="progress-bar" aria-hidden="true">
        <div className="progress-bar-fill" />
      </div>

      <h2>Pipeline Running</h2>
      <p className="progress-note">
        Running in the background — this typically takes{' '}
        <strong>5–10 minutes</strong>. This page polls every 5 seconds.
      </p>

      <ul className="steps-list">
        {STEPS.map((step) => {
          const done    = completedSteps.includes(step.key)
          const active  = !done && currentNode === step.key
          const state   = done ? 'done' : active ? 'active' : 'pending'

          return (
            <li key={step.key} className={`step-item step-${state}`}>
              <span className="step-marker">
                {done && <span className="step-check">✓</span>}
                {active && <span className="step-spinner" />}
                {!done && !active && <span className="step-circle" />}
              </span>
              <div>
                <div className="step-label">{step.label}</div>
                <div className="step-hint">{step.hint}</div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
