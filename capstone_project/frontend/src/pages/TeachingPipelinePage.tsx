import { useCallback, useState } from 'react'
import {
  extractFlowStepsFromBody,
  parseAxiosTeachingError,
  postTeachingTrace,
  teachingDeleteNote,
  teachingGetNote,
  teachingGetPing,
  teachingPostDbMessage,
  teachingPostEcho,
  teachingPostLlm,
  teachingPostNote,
  teachingPutNote,
  type TeachingApiResult,
  type TeachingTracePayload,
} from '../api'
import '../styles/LandingPage.css'
import '../styles/TeachingPipeline.css'

type Props = {
  onBackHome: () => void
}

type OpKey =
  | 'ping'
  | 'echo'
  | 'llm'
  | 'db'
  | 'note_post'
  | 'note_get'
  | 'note_put'
  | 'note_delete'
  | 'pipeline'

function statusClass(status: number): string {
  if (status >= 500) return 'teaching-status-5xx'
  if (status >= 400) return 'teaching-status-4xx'
  if (status >= 200 && status < 300) return 'teaching-status-2xx'
  return 'teaching-status-other'
}

function methodClass(method: string): string {
  const m = method.toUpperCase()
  if (m === 'GET') return 'teaching-method-get'
  if (m === 'POST') return 'teaching-method-post'
  if (m === 'PUT') return 'teaching-method-put'
  if (m === 'DELETE') return 'teaching-method-delete'
  return 'teaching-method-other'
}

const TeachingPipelinePage = ({ onBackHome }: Props) => {
  const [message, setMessage] = useState('Hello — this is my API demo message.')
  const [userEmail, setUserEmail] = useState('demo@oxforduniversity.com')
  const [noteId, setNoteId] = useState('1')
  const [noteContent, setNoteContent] = useState('Example note for PUT/GET/DELETE')
  const [results, setResults] = useState<Partial<Record<OpKey, TeachingApiResult | null>>>({})
  /** Index of last visible architecture row per card (-1 = run completed, no row revealed yet). */
  const [flowReveal, setFlowReveal] = useState<Partial<Record<OpKey, number>>>({})

  const [tracePayload, setTracePayload] = useState<TeachingTracePayload | null>(null)
  const [traceRevealed, setTraceRevealed] = useState(-1)
  const [pipelineLoading, setPipelineLoading] = useState(false)

  const run = useCallback(async (key: OpKey, fn: () => Promise<TeachingApiResult>) => {
    try {
      const r = await fn()
      setResults((s) => ({ ...s, [key]: r }))
      setFlowReveal((s) => ({ ...s, [key]: -1 }))
    } catch (e: unknown) {
      const parsed = parseAxiosTeachingError(e)
      if (parsed) {
        setResults((s) => ({ ...s, [key]: parsed }))
        setFlowReveal((s) => ({ ...s, [key]: -1 }))
      } else
        setResults((s) => ({
          ...s,
          [key]: { method: '?', path: '?', status: 0, body: String(e) },
        }))
    }
  }, [])

  const nextFlowRow = (key: OpKey, flowLen: number) => {
    setFlowReveal((s) => {
      const cur = s[key] ?? -1
      return { ...s, [key]: Math.min(cur + 1, flowLen - 1) }
    })
  }

  const showAllFlowRows = (key: OpKey, flowLen: number) => {
    setFlowReveal((s) => ({ ...s, [key]: flowLen - 1 }))
  }

  const runPipeline = async () => {
    setPipelineLoading(true)
    setTracePayload(null)
    setTraceRevealed(-1)
    try {
      const r = await postTeachingTrace(message.trim(), userEmail.trim())
      setResults((s) => ({ ...s, pipeline: r }))
      setTracePayload(r.body as TeachingTracePayload)
      setTraceRevealed(-1)
    } catch (e: unknown) {
      const parsed = parseAxiosTeachingError(e)
      if (parsed) setResults((s) => ({ ...s, pipeline: parsed }))
    } finally {
      setPipelineLoading(false)
    }
  }

  const steps = tracePayload?.steps ?? []
  const allTraceVisible = tracePayload && traceRevealed >= steps.length - 1 && steps.length > 0

  const renderResult = (key: OpKey) => {
    const r = results[key]
    if (!r) return null
    const flow = extractFlowStepsFromBody(r.body)
    const rev = flowReveal[key] ?? -1
    return (
      <div className="teaching-result">
        <div className="teaching-result-row">
          <span className={`teaching-status-badge ${statusClass(r.status)}`}>{r.status}</span>
          <span className={`teaching-method-badge ${methodClass(r.method)}`}>{r.method}</span>
          <code className="teaching-path">{r.path}</code>
        </div>
        {flow && flow.length > 0 && (
          <div className="teaching-arch">
            <div className="teaching-arch-head">
              <span className="teaching-arch-title">
                Deterministic path: frontend → middleware → route → service → database → LLM
              </span>
              <div className="teaching-arch-btns">
                <button
                  type="button"
                  className="teaching-arch-btn"
                  onClick={() => nextFlowRow(key, flow.length)}
                  disabled={rev >= flow.length - 1}
                >
                  Next row
                </button>
                <button
                  type="button"
                  className="teaching-arch-btn"
                  onClick={() => showAllFlowRows(key, flow.length)}
                >
                  Show all rows
                </button>
              </div>
            </div>
            {flow.map((step, i) => (
              <div
                key={`${key}-flow-${i}`}
                className={`teaching-flow-row ${i <= rev ? 'teaching-flow-row-on' : 'teaching-flow-row-off'}`}
              >
                <span className={`teaching-layer teaching-layer-${step.layer}`}>{step.layer}</span>
                <div className="teaching-flow-text">
                  <strong>{step.title}</strong>
                  <p className="teaching-flow-summary">{step.summary}</p>
                  <p className="teaching-flow-detail">{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        )}
        <p className="teaching-raw-label">Raw JSON (response body)</p>
        <pre className="teaching-json">{JSON.stringify(r.body, null, 2)}</pre>
      </div>
    )
  }

  return (
    <div className="landing-page teaching-lab teaching-lab-light">
      <header className="hero">
        <div className="container">
          <button type="button" className="teaching-back-hero" onClick={onBackHome}>
            ← Back to home
          </button>
          <h1 className="hero-title">API basics lab</h1>
          <p className="hero-subtitle">Whiteboard-style lab — HTTP verbs, status codes, deterministic layers</p>
          <p className="hero-description">
            Send a request, then use <strong>Next row</strong> to reveal how it moves through{' '}
            <strong>middleware</strong>, <strong>routes</strong>, <strong>services</strong>, and{' '}
            <strong>database / LLM</strong> — same order every time (deterministic). Teaching routes only — not{' '}
            <code>/chat</code>.
          </p>
        </div>
      </header>

      <section className="agents-section">
        <div className="container">
          <h2 className="section-title">Shared inputs</h2>
          <div className="teaching-shared-grid">
            <label className="teaching-field">
              Message (echo / LLM / DB row / full pipeline)
              <textarea
                className="teaching-input-light"
                rows={3}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
            </label>
            <label className="teaching-field">
              Email (for DB message + pipeline)
              <input
                className="teaching-input-light"
                type="email"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
              />
            </label>
            <label className="teaching-field">
              Note id (in-memory notes: GET / PUT / DELETE)
              <input
                className="teaching-input-light"
                type="text"
                value={noteId}
                onChange={(e) => setNoteId(e.target.value)}
              />
            </label>
            <label className="teaching-field">
              Note content (create / update)
              <input
                className="teaching-input-light"
                type="text"
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
              />
            </label>
          </div>
        </div>
      </section>

      <section className="features-section">
        <div className="container">
          <h2 className="section-title">Operations</h2>
          <div className="teaching-ops-grid">
            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    📡
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">GET — ping</h3>
                    <p className="agent-description">
                      Frontend → backend only. Typical <strong>200 OK</strong> when the service is healthy.
                    </p>
                  </div>
                </div>
                <button type="button" className="cta-button teaching-card-btn" onClick={() => run('ping', teachingGetPing)}>
                  Send GET
                </button>
              </div>
              {renderResult('ping')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    📤
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">POST — echo</h3>
                    <p className="agent-description">
                      Frontend → backend, <strong>no database</strong>. Response explains <strong>200 OK</strong>.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() => run('echo', () => teachingPostEcho(message.trim()))}
                >
                  Send POST echo
                </button>
              </div>
              {renderResult('echo')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    🤖
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">POST — LLM</h3>
                    <p className="agent-description">
                      Frontend → backend → <strong>LLM only</strong> (no DB in this handler). <strong>200 OK</strong>.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() => run('llm', () => teachingPostLlm(message.trim()))}
                >
                  Send POST LLM
                </button>
              </div>
              {renderResult('llm')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    💾
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">POST — save message (DB)</h3>
                    <p className="agent-description">
                      Frontend → backend → <strong>SQLite</strong> (one row). <strong>201 Created</strong>.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() => run('db', () => teachingPostDbMessage(message.trim(), userEmail.trim()))}
                >
                  Send POST (DB)
                </button>
              </div>
              {renderResult('db')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    📝
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">POST — create note (memory)</h3>
                    <p className="agent-description">
                      In-memory resource for PUT/GET/DELETE demos. <strong>201 Created</strong> with new <code>id</code>.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() => run('note_post', () => teachingPostNote(noteContent.trim()))}
                >
                  Send POST note
                </button>
              </div>
              {renderResult('note_post')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    🔎
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">GET — note by id</h3>
                    <p className="agent-description">
                      <strong>200 OK</strong> if id exists, else <strong>404 Not Found</strong> (try a missing id).
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() => run('note_get', () => teachingGetNote(Number(noteId) || 0))}
                >
                  Send GET note
                </button>
              </div>
              {renderResult('note_get')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    ✏️
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">PUT — update note</h3>
                    <p className="agent-description">
                      <strong>200 OK</strong> if id exists; <strong>404</strong> if not.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() =>
                    run('note_put', () => teachingPutNote(Number(noteId) || 0, noteContent.trim()))
                  }
                >
                  Send PUT note
                </button>
              </div>
              {renderResult('note_put')}
            </div>

            <div className="agent-card teaching-card">
              <div className="teaching-card-row">
                <div className="teaching-card-lead">
                  <span className="agent-icon" aria-hidden>
                    🗑️
                  </span>
                  <div className="teaching-card-copy">
                    <h3 className="agent-title">DELETE — note</h3>
                    <p className="agent-description">
                      Success returns <strong>200 + JSON</strong> here so you can read <code>flow_steps</code> (RFC often uses{' '}
                      <strong>204</strong> with no body). <strong>404</strong> if missing.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button teaching-card-btn"
                  onClick={() => run('note_delete', () => teachingDeleteNote(Number(noteId) || 0))}
                >
                  Send DELETE
                </button>
              </div>
              {renderResult('note_delete')}
            </div>
          </div>
        </div>
      </section>

      <section className="agents-section">
        <div className="container">
          <h2 className="section-title">Full pipeline (DB + LLM, step-by-step)</h2>
          <p className="teaching-pipeline-intro">
            Same teaching route as before: backend → DB (user) → LLM → DB (assistant). Run once, then use{' '}
            <strong>Next step</strong> or <strong>Show all steps</strong>.
          </p>
          <div className="teaching-pipeline-actions">
            <button
              type="button"
              className="cta-button"
              onClick={runPipeline}
              disabled={pipelineLoading || !message.trim()}
            >
              {pipelineLoading ? 'Running…' : 'Run full pipeline trace'}
            </button>
            <button
              type="button"
              className="cta-button teaching-btn-outline"
              onClick={() => tracePayload && setTraceRevealed((i) => Math.min(i + 1, steps.length - 1))}
              disabled={!tracePayload || pipelineLoading || traceRevealed >= steps.length - 1 || steps.length === 0}
            >
              Next step
            </button>
            <button
              type="button"
              className="cta-button teaching-btn-outline"
              onClick={() => tracePayload && setTraceRevealed(steps.length - 1)}
              disabled={!tracePayload || steps.length === 0}
            >
              Show all steps
            </button>
          </div>
          {renderResult('pipeline')}
          {tracePayload && (
            <div className="teaching-trace-steps">
              {steps.map((step, idx) => {
                const visible = idx <= traceRevealed
                return (
                  <div
                    key={`${step.key}-${idx}`}
                    className={`agent-card teaching-trace-card ${visible ? 'teaching-trace-visible' : 'teaching-trace-dim'}`}
                  >
                    <div className="teaching-trace-head">
                      {step.layer && (
                        <span className={`teaching-layer teaching-layer-${step.layer}`}>{step.layer}</span>
                      )}
                      <span>{step.label}</span>
                      <span className="teaching-trace-meta">
                        {step.status} · {step.duration_ms} ms
                      </span>
                    </div>
                    <pre className="teaching-json teaching-json-small">{JSON.stringify(step.detail, null, 2)}</pre>
                  </div>
                )
              })}
            </div>
          )}
          {tracePayload && allTraceVisible && (
            <div className="teaching-final-reply">
              <h3 className="feature-title">Assistant reply</h3>
              <div className="teaching-final-box">{tracePayload.assistant_response}</div>
            </div>
          )}
        </div>
      </section>

      <footer className="footer">
        <div className="container">
          <p>Teaching routes only — Oxford University IT Support demo</p>
        </div>
      </footer>
    </div>
  )
}

export default TeachingPipelinePage
