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
  AlertCircle
} from 'lucide-react';
import TraceExpander from '../components/TraceExpander';
import PlotlyViewer from '../components/PlotlyViewer';
import { sendChatMessage } from '../services/api';

const SAMPLE_PROMPTS = [
  "Which customers are most likely to churn?",
  "What's the churn risk for customer 7590-VHVEG and why?",
  "Now show me a bar chart of churn rate by Contract type.",
  "What if that customer switched to a Two year contract?",
  "Does churn risk correlate with MonthlyCharges?",
  "Average risk by InternetService and Contract"
];

export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I'm your **Autonomous Churn Analyst Agent**. I can analyze telecom customer data, compute churn risks, evaluate retention what-if scenarios, and render interactive charts.\n\nEvery number I report is calculated in real time using tools and verified before display.",
      steps: [],
      charts: [],
      verification: {}
    }
  ]);
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
      setMessages([
        {
          id: 'cleared',
          role: 'assistant',
          content: "Conversation history cleared. Ready for your next customer retention question!",
          steps: [],
          charts: [],
        }
      ]);
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
        <button
          className="btn btn-secondary"
          onClick={handleClear}
          style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
        >
          <Trash2 size={14} /> Clear Context
        </button>
      </div>

      {/* Suggested Prompts */}
      <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.75rem', marginBottom: '0.75rem' }}>
        {SAMPLE_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(prompt)}
            style={{
              padding: '0.4rem 0.85rem',
              borderRadius: 'var(--radius-full)',
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: 'var(--text-secondary)',
              fontSize: '0.76rem',
              fontWeight: 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)';
              e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(30, 41, 59, 0.7)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            {prompt}
          </button>
        ))}
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
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                gap: '0.85rem',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: isUser ? '80%' : '90%',
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
                background: isUser ? 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)' : 'rgba(30, 41, 59, 0.6)',
                border: isUser ? '1px solid rgba(129, 140, 248, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                padding: '1rem 1.25rem',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
              }}>
                <div style={{
                  fontSize: '0.92rem',
                  lineHeight: 1.6,
                  color: '#f8fafc',
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.content}
                </div>

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
            }}>
              <Loader2 size={16} className="animate-spin" />
            </div>
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              borderRadius: '16px 16px 16px 4px',
              padding: '0.9rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              color: '#a5b4fc',
              fontSize: '0.88rem',
            }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
              <span>{activeStepText}</span>
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
          placeholder="Ask a question (e.g. Which customers are most likely to churn?)"
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
