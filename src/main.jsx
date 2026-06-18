import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  Bot,
  CalendarCheck,
  CheckCircle2,
  Cloud,
  Database,
  Headphones,
  HeartPulse,
  Mic,
  PhoneCall,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRound,
  Volume2
} from "lucide-react";
import "./styles.css";

const BACKEND_URL = "https://voice-agent-ai-3omf.onrender.com";

const chatMessages = [
  { from: "Patient", text: "I need a gastroenterology appointment on Tuesday." },
  { from: "AI", text: "Dr. Somya Agarwal is available at 10:00 AM and 11:00 AM." },
  { from: "Patient", text: "Book 11 AM." },
  { from: "AI", text: "Your appointment is confirmed. Booking ID: APT-CV90." },
  { from: "Patient", text: "Cancel my booking." },
  { from: "AI", text: "Please provide your booking ID." },
  { from: "Patient", text: "APT-CV90." },
  { from: "AI", text: "Your appointment has been cancelled successfully." }
];

const features = [
  {
    icon: CalendarCheck,
    title: "Check doctor availability",
    text: "Looks up OPD slots by day, specialty, and doctor schedule."
  },
  {
    icon: PhoneCall,
    title: "Book appointments",
    text: "Confirms a booking only after checking Firestore for conflicts."
  },
  {
    icon: ShieldCheck,
    title: "Cancel using booking ID",
    text: "Patients can cancel with a short code like APT-7K3P."
  },
  {
    icon: RefreshCcw,
    title: "Reschedule using booking ID",
    text: "Moves appointments only when the requested new slot is free."
  },
  {
    icon: Database,
    title: "Firestore backend",
    text: "Doctors and appointments are stored in Firebase Firestore."
  },
  {
    icon: Bot,
    title: "Voice AI assistant",
    text: "Designed for Vapi tool calls and natural phone conversations."
  }
];

function App() {
  const [apiStatus, setApiStatus] = useState({
    loading: true,
    online: false,
    database: "Checking...",
    firebaseConnected: false,
    message: "Connecting to Render backend..."
  });
  const [voiceStarted, setVoiceStarted] = useState(false);

  const vapiPublicKey = import.meta.env.VITE_VAPI_PUBLIC_KEY;
  const vapiAssistantId = import.meta.env.VITE_VAPI_ASSISTANT_ID;
  const vapiConfigured = Boolean(vapiPublicKey && vapiAssistantId);

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      try {
        const response = await fetch(`${BACKEND_URL}/health`, {
          signal: controller.signal
        });
        const data = await response.json();
        setApiStatus({
          loading: false,
          online: response.ok && Boolean(data.success),
          database: data.database || "Unknown",
          firebaseConnected: Boolean(data.firebase_configured),
          message: data.firebase_message || "Backend responded successfully."
        });
      } catch (error) {
        if (error.name === "AbortError") return;
        setApiStatus({
          loading: false,
          online: false,
          database: "Unavailable",
          firebaseConnected: false,
          message: "Backend is not reachable from this browser right now."
        });
      }
    }

    checkBackend();
    return () => controller.abort();
  }, []);

  const statusTone = useMemo(() => {
    if (apiStatus.loading) return "checking";
    return apiStatus.online ? "online" : "offline";
  }, [apiStatus]);

  function handleVoiceClick() {
    if (!vapiConfigured) return;
    setVoiceStarted((current) => !current);
  }

  return (
    <main>
      <section className="hero section-shell">
        <nav className="topbar" aria-label="Project navigation">
          <a className="brand" href="#top" aria-label="Voice AI Hospital Agent home">
            <span className="brand-mark">
              <HeartPulse size={20} />
            </span>
            <span>Voice OPD Agent</span>
          </a>
          <div className="nav-actions">
            <a href="#workflow">Workflow</a>
            <a href="#demo">Demo</a>
          </div>
        </nav>

        <div className="hero-grid" id="top">
          <div className="hero-copy">
            <span className="eyebrow">
              <Sparkles size={16} />
              Flask + Vapi + Firestore
            </span>
            <h1>Book your hospital appointment with Voice AI</h1>
            <p>
              A demo AI receptionist that can check doctor availability, book appointments,
              cancel bookings, and reschedule using a booking ID.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#voice-demo">
                <Mic size={18} />
                Launch Voice Demo
              </a>
              <a className="button secondary" href="#workflow">
                View Workflow
                <ArrowRight size={18} />
              </a>
            </div>
          </div>

          <div className="hero-panel" aria-label="Live backend summary">
            <div className="panel-header">
              <div>
                <span className={`status-dot ${statusTone}`} />
                API status
              </div>
              <Activity size={18} />
            </div>
            <div className="metric-row">
              <span>Backend</span>
              <strong>{apiStatus.loading ? "Checking" : apiStatus.online ? "Online" : "Offline"}</strong>
            </div>
            <div className="metric-row">
              <span>Database</span>
              <strong>{apiStatus.database}</strong>
            </div>
            <div className="metric-row">
              <span>Firebase</span>
              <strong>{apiStatus.firebaseConnected ? "Connected" : "Not connected"}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="demo-section section-shell" id="demo">
        <div className="section-heading">
          <span className="eyebrow">
            <Headphones size={16} />
            Conversation demo
          </span>
          <h2>Book your appointment in seconds</h2>
          <p>
            The voice assistant translates natural conversation into API calls for availability,
            booking, cancellation, and rescheduling.
          </p>
        </div>

        <div className="conversation-board">
          <div className="chat-window" aria-label="Appointment conversation example">
            <div className="chat-toolbar">
              <div>
                <span />
                <span />
                <span />
              </div>
              <p>AI receptionist session</p>
            </div>
            <div className="messages">
              {chatMessages.map((message, index) => (
                <div
                  className={`message ${message.from === "AI" ? "ai" : "patient"}`}
                  key={`${message.from}-${index}`}
                >
                  <span>{message.from}</span>
                  <p>{message.text}</p>
                </div>
              ))}
            </div>
          </div>

          <aside className="voice-bar" aria-label="Voice assistant status">
            <div className="voice-orb">
              <Volume2 size={28} />
            </div>
            <div className="wave-stack" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="voice-stat">
              <span>Tool calls</span>
              <strong>4</strong>
            </div>
            <div className="voice-stat">
              <span>Booking ID</span>
              <strong>APT-CV90</strong>
            </div>
            <div className="voice-stat">
              <span>Status</span>
              <strong>Handled</strong>
            </div>
          </aside>
        </div>
      </section>

      <section className="voice-demo section-shell" id="voice-demo">
        <div className="live-card">
          <div>
            <span className="eyebrow">
              <Mic size={16} />
              Live Voice Demo
            </span>
            <h2>Vapi Web SDK placeholder</h2>
            <p>
              {vapiConfigured
                ? "Vapi environment variables are configured. This button is ready for SDK wiring."
                : "Voice demo will be connected here. Backend APIs are live."}
            </p>
          </div>
          <button
            className="button primary voice-button"
            onClick={handleVoiceClick}
            disabled={!vapiConfigured}
            type="button"
          >
            <Mic size={18} />
            {voiceStarted ? "Voice Assistant Ready" : "Start Voice Assistant"}
          </button>
        </div>
      </section>

      <section className="status-section section-shell" id="status">
        <div className="section-heading">
          <span className="eyebrow">
            <Cloud size={16} />
            API Status
          </span>
          <h2>Live backend connection</h2>
        </div>
        <div className="status-grid">
          <StatusCard
            label="Backend"
            value={apiStatus.loading ? "Checking..." : apiStatus.online ? "Online" : "Offline"}
            active={apiStatus.online}
          />
          <StatusCard label="Database" value={apiStatus.database} active={apiStatus.database === "Firestore"} />
          <StatusCard
            label="Firebase"
            value={apiStatus.firebaseConnected ? "Connected" : "Not connected"}
            active={apiStatus.firebaseConnected}
          />
        </div>
        <p className="status-note">{apiStatus.message}</p>
      </section>

      <section className="features section-shell">
        <div className="section-heading">
          <span className="eyebrow">
            <Stethoscope size={16} />
            Product capabilities
          </span>
          <h2>Built for a real appointment workflow</h2>
        </div>
        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.title}>
              <feature.icon size={24} />
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="architecture section-shell" id="workflow">
        <div className="section-heading">
          <span className="eyebrow">
            <Database size={16} />
            Architecture
          </span>
          <h2>From voice request to Firestore update</h2>
        </div>
        <div className="flow">
          <FlowNode icon={UserRound} title="User" text="Speaks naturally" />
          <FlowNode icon={Mic} title="Website / Vapi Voice Agent" text="Collects appointment details" />
          <FlowNode icon={Cloud} title="Flask API on Render" text="Validates and handles booking logic" />
          <FlowNode icon={Database} title="Firebase Firestore" text="Stores doctors and appointments" />
        </div>
      </section>

      <section className="notice section-shell">
        <div className="notice-card">
          <ShieldCheck size={26} />
          <div>
            <h2>Demo notice</h2>
            <p>
              This is a demo project for engineering evaluation and portfolio presentation.
              It does not create real hospital appointments. Doctor names, timings, and hospital
              information are based on publicly available sample data used only for demonstration.
              Users should not treat this system as an official hospital booking service. No medical
              advice is provided. Do not enter sensitive personal or medical information.
            </p>
          </div>
        </div>
      </section>

      <footer>
        Built by Pratik Raj - Voice AI Agent Engineering Assignment
      </footer>
    </main>
  );
}

function StatusCard({ label, value, active }) {
  return (
    <article className="status-card">
      <span className={`status-dot ${active ? "online" : "offline"}`} />
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function FlowNode({ icon: Icon, title, text }) {
  return (
    <article className="flow-node">
      <div>
        <Icon size={22} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
