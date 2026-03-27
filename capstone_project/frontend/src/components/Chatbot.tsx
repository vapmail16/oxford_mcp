import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from '../api'
import '../styles/Chatbot.css'

/** MCP / agentic demo trace from POST /chat (Agentic MCP track). */
export type McpTrace = {
  how_agentic_works?: string
  where_is_ai?: string
  no_tool_match?: boolean
  why_no_mcp_call?: string
  example_prompts_that_work?: string[]
  tool_selection?: {
    decided_by?: string | null
    confidence?: number | null
    params_passed_to_tool?: Record<string, unknown> | null
    note?: string | null
  }
  tool?: string | null
  success?: boolean
  result_summary?: string
  transport?: string | null
}

export type ChatApiResponse = {
  response: string
  session_id: string
  sources?: string[]
  ticket_id?: number | null
  demo_track?: string | null
  presenter?: Record<string, string> | null
  mcp_trace?: McpTrace | null
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  ticket_id?: number | null
  presenter?: Record<string, string>
  mcp_trace?: McpTrace | null
}

/** One suggested prompt under a demo track */
export type DemoQuestion = {
  label: string
  message: string
  demo_track?: string
}

export type DemoSection = {
  id: string
  label: string
  description: string
  questions: DemoQuestion[]
}

/** Main sections → each has its own questions (then user sees the answer). */
const DEMO_SECTIONS: DemoSection[] = [
  {
    id: 'menu',
    label: 'Demo menu',
    description: 'Show the cohort demo menu in chat',
    questions: [{ label: 'Show welcome & track list', message: 'Hi' }],
  },
  {
    id: 'plain_llm',
    label: 'Direct LLM',
    description: 'Language model only — no knowledge base or tools',
    questions: [
      {
        label: 'Password best practice (one sentence)',
        message: 'Give one password best practice in one sentence.',
        demo_track: 'plain_llm',
      },
      {
        label: 'Explain phishing briefly',
        message: 'Explain what phishing is in two sentences for a non-technical employee.',
        demo_track: 'plain_llm',
      },
    ],
  },
  {
    id: 'rag_kb',
    label: 'KB RAG',
    description: 'Retrieve from the IT knowledge base (Qdrant), then answer',
    questions: [
      {
        label: 'VPN error 422 when connecting',
        message: "I'm getting VPN error 422 when trying to connect",
        demo_track: 'rag_kb',
      },
      { label: 'Reset my password', message: 'I need to reset my password', demo_track: 'rag_kb' },
      { label: 'WiFi is slow', message: 'My WiFi is slow', demo_track: 'rag_kb' },
      { label: 'How do I install software?', message: 'How do I install software?', demo_track: 'rag_kb' },
      {
        label: 'Error code 0x80070005',
        message: "I'm seeing error code 0x80070005",
        demo_track: 'rag_kb',
      },
    ],
  },
  {
    id: 'rag_db',
    label: 'DB RAG',
    description: 'RAG over embedded tickets and messages (structured)',
    questions: [
      {
        label: 'Summarize VPN / network tickets',
        message: 'Summarize recent internal tickets that mention VPN or network.',
        demo_track: 'rag_db',
      },
      {
        label: 'Recent password / access themes',
        message: 'What themes appear in recent tickets about password or access?',
        demo_track: 'rag_db',
      },
    ],
  },
  {
    id: 'agentic_mcp',
    label: 'Agentic MCP',
    description: 'Triage → ticket → reply, each step via MCP (stdio when enabled)',
    questions: [
      { label: 'Check my VPN status', message: 'Check my VPN status', demo_track: 'agentic_mcp' },
      {
        label: 'Start a password reset',
        message: 'Start a password reset for my account',
        demo_track: 'agentic_mcp',
      },
    ],
  },
]

/** When user types in the box on step 2, send this track (section id === API demo_track, except menu). */
function demoTrackForSectionId(sectionId: string): string | undefined {
  if (sectionId === 'menu') return undefined
  return sectionId
}

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [userEmail, setUserEmail] = useState('demo@acmecorp.com')
  const [isLoading, setIsLoading] = useState(false)
  /** `null` = step 1 (pick track); section id = step 2 (pick question) */
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null)
  /**
   * Sticky demo track for the whole thread. Without this, only the first request
   * sent `demo_track` (see trackFromWelcome), so follow-ups hit legacy RAG/KB
   * even when the user picked Direct LLM.
   */
  const [activeDemoTrack, setActiveDemoTrack] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  useEffect(() => scrollToBottom(), [messages])

  const resetToHomeScreen = () => {
    setMessages([])
    setSessionId(null)
    setSelectedSectionId(null)
    setActiveDemoTrack(null)
    setInput('')
  }

  const postChat = async (message: string, demo_track?: string) => {
    const { data } = await api.post<ChatApiResponse>('/chat', {
      message,
      session_id: sessionId ?? undefined,
      user_email: userEmail,
      demo_mode: true,
      ...(demo_track ? { demo_track } : {}),
    })
    return data
  }

  const selectedSection = selectedSectionId
    ? DEMO_SECTIONS.find((s) => s.id === selectedSectionId) ?? null
    : null

  /** After user picks a question under a track */
  const handleTrackQuestion = (q: DemoQuestion, sectionLabel: string) => {
    setInput('')
    setSelectedSectionId(null)
    const sticky =
      q.demo_track ??
      (selectedSectionId && selectedSectionId !== 'menu' ? selectedSectionId : null)
    if (sticky && sticky !== 'menu') {
      setActiveDemoTrack(sticky)
    } else if (selectedSectionId === 'menu') {
      setActiveDemoTrack(null)
    }
    const visible = q.demo_track ? `[${sectionLabel}] ${q.message}` : q.message
    setMessages((prev) => [...prev, { role: 'user', content: visible }])
    setIsLoading(true)
    postChat(q.message, q.demo_track)
      .then((data) => {
        setSessionId(data.session_id)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.response,
            ticket_id: data.ticket_id ?? undefined,
            presenter: data.presenter ?? undefined,
            mcp_trace: data.mcp_trace ?? undefined,
          },
        ])
      })
      .catch(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Sorry, I encountered an error. Is the backend running on port 8000?',
          },
        ])
      })
      .finally(() => setIsLoading(false))
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    const messageToSend = input.trim()
    if (!messageToSend || isLoading) return

    /** First message while a section is open: use that track (e.g. Direct LLM = plain_llm). */
    const trackFromWelcome =
      messages.length === 0 && selectedSectionId
        ? demoTrackForSectionId(selectedSectionId)
        : undefined
    const trackToSend =
      trackFromWelcome ??
      (activeDemoTrack && activeDemoTrack !== 'menu' ? activeDemoTrack : undefined)

    setInput('')
    setSelectedSectionId(null)
    setMessages((prev) => [...prev, { role: 'user', content: messageToSend }])
    setIsLoading(true)

    try {
      const data = await postChat(messageToSend, trackToSend)
      setSessionId(data.session_id)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          ticket_id: data.ticket_id ?? undefined,
          presenter: data.presenter ?? undefined,
          mcp_trace: data.mcp_trace ?? undefined,
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please ensure the backend is running on port 8000.',
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <button
        className="chatbot-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle chatbot"
      >
        💬
      </button>

      {isOpen && (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <h3>IT Support Chatbot</h3>
            <div className="chatbot-header-email">
              <label>Email:</label>
              <input
                type="email"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                className="chatbot-email-input"
              />
            </div>
            <button
              className="chatbot-close"
              onClick={() => setIsOpen(false)}
              aria-label="Close chatbot"
            >
              ×
            </button>
          </div>

          <div className="chatbot-messages">
            {messages.length > 0 && (
              <div className="chatbot-messages-toolbar">
                <button
                  type="button"
                  className="chatbot-back-to-menu"
                  onClick={resetToHomeScreen}
                  disabled={isLoading}
                  aria-label="Back to demo tracks"
                >
                  ← Back to menu
                </button>
              </div>
            )}
            {messages.length === 0 && (
              <div className="chatbot-welcome">
                <p>Hello! I'm your IT Support assistant. How can I help you today?</p>

                {!selectedSection && (
                  <>
                    <p className="demo-wizard-hint">
                      <strong>Step 1 of 2:</strong> choose a demo track.{' '}
                      <strong>Step 2:</strong> pick a question — then you’ll see the answer.
                    </p>
                    <div className="chatbot-demo-strip">
                      <p className="demo-strip-label">Oxford / cohort demo tracks</p>
                      <div className="demo-strip-buttons">
                        {DEMO_SECTIONS.map((section) => (
                          <button
                            key={section.id}
                            type="button"
                            className="demo-track-button"
                            onClick={() => {
                              setSelectedSectionId(section.id)
                              setActiveDemoTrack(section.id === 'menu' ? null : section.id)
                            }}
                            disabled={isLoading}
                          >
                            {section.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {selectedSection && (
                  <div className="demo-section-questions">
                    <button
                      type="button"
                      className="demo-back-to-tracks"
                      onClick={() => setSelectedSectionId(null)}
                      disabled={isLoading}
                    >
                      ← Back to tracks
                    </button>
                    <p className="demo-section-title">{selectedSection.label}</p>
                    <p className="demo-section-desc">{selectedSection.description}</p>
                    <p className="questions-label">Pick a question</p>
                    <div className="questions-grid">
                      {selectedSection.questions.map((q, i) => (
                        <button
                          key={`${selectedSection.id}-${i}`}
                          type="button"
                          className="question-button"
                          onClick={() => handleTrackQuestion(q, selectedSection.label)}
                          disabled={isLoading}
                        >
                          {q.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            {messages.map((message, index) => (
              <div
                key={index}
                className={`message ${message.role === 'user' ? 'message-user' : 'message-assistant'}`}
              >
                <div className="message-content">
                  {message.role === 'assistant' ? (
                    <>
                      {message.ticket_id != null && message.ticket_id > 0 && (
                        <div
                          className="chatbot-ticket-badge"
                          title="Created in SQLite by the escalation path"
                        >
                          Ticket #{message.ticket_id}
                        </div>
                      )}
                      <div className="message-markdown">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                      </div>
                      {(message.presenter || message.mcp_trace) && (
                        <details className="chatbot-presenter-details">
                          <summary>Presenter / code &amp; MCP trace</summary>
                          {message.mcp_trace?.no_tool_match && (
                            <div className="chatbot-agentic-no-match">
                              <strong>Why nothing was sent to MCP</strong>
                              <p>{message.mcp_trace.why_no_mcp_call}</p>
                              <p className="chatbot-agentic-examples">
                                <strong>Try instead (end-to-end demo):</strong>
                                <ul>
                                  {(message.mcp_trace.example_prompts_that_work ?? []).map(
                                    (p) => (
                                      <li key={p}>
                                        <code>{p}</code>
                                      </li>
                                    )
                                  )}
                                </ul>
                              </p>
                            </div>
                          )}
                          {message.mcp_trace?.success === true &&
                            Boolean(message.mcp_trace.tool) && (
                            <div className="chatbot-agentic-summary">
                              <strong>How the agent picked the tool</strong>
                              <p>
                                Tool <code>{message.mcp_trace.tool}</code> was chosen{' '}
                                <strong>
                                  {message.mcp_trace.tool_selection?.decided_by === 'llm'
                                    ? 'by the LLM'
                                    : message.mcp_trace.tool_selection?.decided_by ===
                                        'rule_based'
                                      ? 'by rule-based routing (fallback)'
                                      : `(${message.mcp_trace.tool_selection?.decided_by ?? 'unknown'})`}
                                </strong>
                                {message.mcp_trace.tool_selection?.confidence != null && (
                                  <>
                                    {' '}
                                    with confidence{' '}
                                    <span className="chatbot-confidence">
                                      {String(message.mcp_trace.tool_selection.confidence)}
                                    </span>
                                  </>
                                )}
                                . Params sent to MCP:{' '}
                                <code className="chatbot-params-snippet">
                                  {JSON.stringify(
                                    message.mcp_trace.tool_selection?.params_passed_to_tool ??
                                      {}
                                  )}
                                </code>
                              </p>
                            </div>
                          )}
                          {message.presenter && (
                            <pre className="chatbot-meta-block">
                              {JSON.stringify(message.presenter, null, 2)}
                            </pre>
                          )}
                          {message.mcp_trace && (
                            <pre className="chatbot-meta-block">
                              {JSON.stringify(message.mcp_trace, null, 2)}
                            </pre>
                          )}
                        </details>
                      )}
                    </>
                  ) : (
                    message.content
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message message-assistant">
                <div className="message-content">
                  <span className="typing-indicator">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chatbot-input-form" onSubmit={handleSendMessage}>
            <input
              type="text"
              className="chatbot-input"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
            <button
              type="submit"
              className="chatbot-send"
              disabled={isLoading || !input.trim()}
              aria-label="Send message"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </>
  )
}

export default Chatbot
