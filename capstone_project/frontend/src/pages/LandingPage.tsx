import '../styles/LandingPage.css'

type LandingPageProps = {
  onOpenTeaching?: () => void
}

const LandingPage = ({ onOpenTeaching }: LandingPageProps) => {
  return (
    <div className="landing-page">
      <header className="hero">
        <div className="container">
          <h1 className="hero-title">IT Support Agent</h1>
          <p className="hero-subtitle">Intelligent System Management Platform</p>
          <p className="hero-description">
            Diagnose issues, search the knowledge base, create tickets, and get AI-powered support
          </p>
          {onOpenTeaching && (
            <button type="button" className="hero-teaching-btn" onClick={onOpenTeaching}>
              API basics lab
            </button>
          )}
        </div>
      </header>

      <section className="agents-section">
        <div className="container">
          <h2 className="section-title">AI-Powered Agents</h2>
          <div className="agents-grid">
            <div className="agent-card">
              <div className="agent-icon">📊</div>
              <h3 className="agent-title">Triage Agent</h3>
              <p className="agent-description">
                Automatically classify issues by intent, category, and priority to route
                your request to the right resolution path.
              </p>
            </div>
            <div className="agent-card">
              <div className="agent-icon">🔍</div>
              <h3 className="agent-title">RAG Agent</h3>
              <p className="agent-description">
                Search our knowledge base for VPN guides, password reset SOPs, WiFi
                troubleshooting, and common error codes.
              </p>
            </div>
            <div className="agent-card">
              <div className="agent-icon">⚡</div>
              <h3 className="agent-title">Ticket Agent</h3>
              <p className="agent-description">
                Create and manage support tickets automatically. Track status and
                get updates on your IT issues.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="features-section">
        <div className="container">
          <h2 className="section-title">Key Features</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🧠</div>
              <h3 className="feature-title">RAG Technology</h3>
              <p className="feature-description">
                Retrieval-Augmented Generation for accessing troubleshooting guides,
                error logs, and configuration documents instantly.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔌</div>
              <h3 className="feature-title">MCP Integration</h3>
              <p className="feature-description">
                Model Context Protocol with system monitoring APIs and device
                management commands for seamless operations.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">💾</div>
              <h3 className="feature-title">Session Memory</h3>
              <p className="feature-description">
                Persistent conversation history for multi-turn support and
                personalized assistance.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="cta-section">
        <div className="container">
          <h2 className="cta-title">Ready to Transform Your IT Support?</h2>
          <p className="cta-description">
            Click the chat button below to get started
          </p>
          <button className="cta-button" onClick={() => document.querySelector<HTMLButtonElement>('.chatbot-toggle')?.click()}>
            Get Started
          </button>
        </div>
      </section>

      <footer className="footer">
        <div className="container">
          <p>&copy; 2024 IT Support Agent. Acme Corp. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
