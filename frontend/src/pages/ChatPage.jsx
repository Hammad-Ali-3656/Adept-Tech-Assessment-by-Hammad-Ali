import React, { useState, useRef, useEffect } from 'react';
import { 
  BotMessageSquare, 
  Send, 
  Trash2, 
  Sparkles, 
  ShieldCheck, 
  BarChart3, 
  Terminal,
  Loader2,
  Database,
  Layers,
  Zap,
  CheckCircle2,
  UserCheck
} from 'lucide-react';
import TraceExpander from '../components/TraceExpander';
import PlotlyViewer from '../components/PlotlyViewer';
import FormattedMessage from '../components/FormattedMessage';
import { sendChatMessage } from '../services/api';

const PROMPT_CATEGORIES = [
  {
    icon: Sparkles,
    label: "Top Churn Drivers",
    prompt: "Which customers are most likely to churn and what are the main reasons?",
  },
  {
    icon: UserCheck,
    label: "Account Risk Score",
    prompt: "What is the churn risk for customer 7590-VHVEG and why?",
  },
  {
    icon: BarChart3,
    label: "Contract Distribution",
    prompt: "Show me a bar chart of churn rate by Contract type.",
  },
  {
    icon: Zap,
    label: "What-If Simulation",
    prompt: "What if customer 7590-VHVEG switched to a Two year contract?",
  },
  {
    icon: Layers,
    label: "Internet Service Breakdown",
    prompt: "Compare average churn risk and monthly charges by InternetService.",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeStepText, setActiveStepText] = useState('Planning → computing → verifying…');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (questionToSend) => {
    const q = (questionToSend || input).trim();
    if (!q || loading) return;

    setInput('');
    const userMsg = { id: `u_${Date.now()}`, role: 'user', content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setActiveStepText('Planning tool calls & executing sandboxed computation…');

    try {
      const res = await sendChatMessage(q);
      const assistantMsg = {
        id: `a_${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        charts: res.charts || [],
        steps: res.steps || [],
        verification: res.verification || {},
        ok: res.ok,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Error communicating with agent:** ${err.message}. Please verify the backend is running.`,
          steps: [`error: ${err.message}`],
          charts: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    try {
      await sendChatMessage('', true);
      setMessages([]);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="page-wrapper animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 4rem)', maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#818cf8', fontSize: '0.78rem', fontWeight: 600 }}>
            <BotMessageSquare size={15} /> Autonomous Data Analyst
          </div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Ask About Your Customers</h2>
        </div>
        {messages.length > 0 && (
          <button
            className="btn btn-secondary"
            onClick={handleClear}
            style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
          >
            <Trash2 size={14} /> Clear Context
          </button>
        )}
      </div>

      {/* Chat Messages Container */}
      <div className="glass-panel" style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
        marginBottom: '1rem',
        background: 'rgba(11, 15, 25, 0.65)',
      }}>
        {/* Welcome Card if no messages */}
        {messages.length === 0 && (
          <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
            <div className="glass-card" style={{
              padding: '2rem',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              marginBottom: '1.5rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1rem' }}>
                <div style={{
                  width: 44,
                  height: 44,
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  boxShadow: '0 6px 20px rgba(99, 102, 241, 0.4)',
                }}>
                  <Sparkles size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.35rem', fontWeight: 800 }}>
                    Welcome to the <span className="text-gradient">Autonomous Churn Analyst</span>
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    Natural-language telemetry analytics powered by tool-grounded AI computation.
                  </p>
                </div>
              </div>

              {/* 3 Value Pillars */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginTop: '1.25rem' }}>
                <div style={{ padding: '1rem', background: 'rgba(15, 23, 42, 0.6)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                    <Database size={15} /> Real Tool Computation
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    Runs sandboxed pandas operations directly against 7,043 customer records — never guessing from memory.
                  </div>
                </div>

                <div style={{ padding: '1rem', background: 'rgba(15, 23, 42, 0.6)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34d399', fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                    <ShieldCheck size={15} /> Zero Hallucinations
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    Every figure and percentage in answers is deterministically checked against executed tool outputs.
                  </div>
                </div>

                <div style={{ padding: '1rem', background: 'rgba(15, 23, 42, 0.6)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fde68a', fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                    <Zap size={15} /> What-If Simulations
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    Projects retention outcomes under counterfactual contract, discount, and support scenarios.
                  </div>
                </div>
              </div>
            </div>

            {/* Prompt Starter Chips */}
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              Suggested Inquiries:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
              {PROMPT_CATEGORIES.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => handleSend(item.prompt)}
                    style={{
                      padding: '0.85rem 1rem',
                      background: 'rgba(30, 41, 59, 0.6)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.75rem',
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)';
                      e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    <div style={{ padding: '0.35rem', borderRadius: 6, background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', marginTop: 2 }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f8fafc' }}>{item.label}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>"{item.prompt}"</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Message History */}
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                gap: '0.85rem',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: isUser ? '80%' : '92%',
              }}
            >
              {!isUser && (
                <div style={{
                  width: 34,
                  height: 34,
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  flexShrink: 0,
                  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                }}>
                  <Sparkles size={16} />
                </div>
              )}

              <div style={{
                background: isUser ? 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)' : 'rgba(30, 41, 59, 0.65)',
                border: isUser ? '1px solid rgba(129, 140, 248, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                padding: '1rem 1.25rem',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
              }}>
                <FormattedMessage content={msg.content} />

                {/* Rendered Charts */}
                {msg.charts && msg.charts.map((fig, idx) => (
                  <PlotlyViewer key={idx} figureJson={fig} />
                ))}

                {/* Agent Execution Trace */}
                {!isUser && msg.steps && msg.steps.length > 0 && (
                  <TraceExpander steps={msg.steps} verification={msg.verification} />
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div style={{ display: 'flex', gap: '0.85rem', alignSelf: 'flex-start', maxWidth: '85%' }}>
            <div style={{
              width: 34,
              height: 34,
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              flexShrink: 0,
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
            }}>
              <Loader2 size={16} className="animate-spin" />
            </div>
            <div style={{
              background: 'rgba(30, 41, 59, 0.65)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              borderRadius: '16px 16px 16px 4px',
              padding: '0.9rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              color: '#a5b4fc',
              fontSize: '0.88rem',
            }}>
              <Loader2 size={16} className="animate-spin" style={{ color: '#818cf8' }} />
              <span>{activeStepText}</span>
              <div style={{ display: 'inline-flex', gap: '4px', marginLeft: '4px', alignItems: 'center' }}>
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Chat Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        style={{
          display: 'flex',
          gap: '0.75rem',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: 'var(--radius-md)',
          padding: '0.4rem 0.5rem 0.4rem 1.2rem',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a customer retention question (e.g. Which customers are most likely to churn?)..."
          disabled={loading}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#fff',
            fontFamily: 'var(--font-body)',
            fontSize: '0.92rem',
          }}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="btn btn-primary"
          style={{
            borderRadius: 'var(--radius-sm)',
            padding: '0.6rem 1.1rem',
            opacity: !input.trim() || loading ? 0.6 : 1,
          }}
        >
          <Send size={16} /> Send
        </button>
      </form>
    </div>
  );
}
