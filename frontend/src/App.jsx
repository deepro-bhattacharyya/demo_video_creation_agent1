import { useState, useEffect, useCallback } from 'react'
import PipelineForm from './components/PipelineForm'
import ProgressView from './components/ProgressView'
import SceneReviewer from './components/SceneReviewer'
import ResultsView from './components/ResultsView'
import { startPipeline, getStatus, resumePipeline } from './api'

const POLL_MS = 5000

export default function App() {
  const [view, setView] = useState('idle')        // idle | running | awaiting_review | done | error
  const [threadId, setThreadId] = useState(null)
  const [scenes, setScenes] = useState([])
  const [customInstructions, setCustomInstructions] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Poll for job status while the pipeline is running in the background.
  useEffect(() => {
    if (view !== 'running' || !threadId) return
    const id = setInterval(async () => {
      try {
        const data = await getStatus(threadId)
        if (data.status === 'awaiting_review') {
          setScenes(data.scenes ?? [])
          setCustomInstructions(data.custom_instructions ?? '')
          setView('awaiting_review')
        } else if (data.status === 'done') {
          setResult(data)
          setView('done')
        } else if (data.status === 'error') {
          setError(data.error ?? 'An unknown error occurred.')
          setView('error')
        }
        // status === 'running' → keep polling
      } catch (e) {
        setError(e.message)
        setView('error')
      }
    }, POLL_MS)
    return () => clearInterval(id)
  }, [view, threadId])

  const handleStart = useCallback(async (formData) => {
    setError(null)
    try {
      const data = await startPipeline(formData)
      setThreadId(data.thread_id)
      setView('running')
    } catch (e) {
      setError(e.message)
      setView('error')
    }
  }, [])

  const handleResume = useCallback(async (action, editedScenes) => {
    setView('running')
    try {
      await resumePipeline(threadId, action, editedScenes)
      // polling will pick up the updated status
    } catch (e) {
      setError(e.message)
      setView('error')
    }
  }, [threadId])

  const handleReset = () => {
    setView('idle')
    setThreadId(null)
    setScenes([])
    setResult(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <h1>DemoVideoBot</h1>
          <p>Automated demo video generator for AgenticQEAHub agents</p>
        </div>
      </header>

      <main className="app-main">
        {view === 'idle'            && <PipelineForm onSubmit={handleStart} />}
        {view === 'running'         && <ProgressView />}
        {view === 'awaiting_review' && (
          <SceneReviewer
            scenes={scenes}
            customInstructions={customInstructions}
            onResume={handleResume}
          />
        )}
        {view === 'done'  && <ResultsView result={result} onReset={handleReset} />}
        {view === 'error' && (
          <div className="card error-card">
            <h2>Pipeline Error</h2>
            <pre>{error}</pre>
            <button className="btn-primary" onClick={handleReset}>Try Again</button>
          </div>
        )}
      </main>
    </div>
  )
}
