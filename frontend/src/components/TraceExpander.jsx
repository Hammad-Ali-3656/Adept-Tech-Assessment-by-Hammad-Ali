import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Terminal, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function TraceExpander({ steps = [], verification = {} }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!steps || steps.length === 0) return null;

  const isCriticPass = steps.some(s => s.toLowerCase().includes('critic: pass'));
  const isCaution = verification?.flagged || steps.some(s => s.toLowerCase().includes('fail'));

  return (
    <div style={{
      marginTop: '1rem',
      borderRadius: 'var(--radius-sm)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      background: 'rgba(15, 23, 42, 0.6)',
      overflow: 'hidden',
    }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.65rem 1rem',
          background: 'transparent',
          border: 'none',
          color: 'var(--text-secondary)',
          fontSize: '0.8rem',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'background 0.2s ease',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Terminal size={14} color="var(--primary-light)" />
          <span>Agent Execution Trace ({steps.length} steps)</span>
          {isCriticPass && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: '#34d399', fontSize: '0.75rem' }}>
              <ShieldCheck size={13} /> Verified
            </span>
          )}
          {isCaution && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: '#fbbf24', fontSize: '0.75rem' }}>
              <AlertTriangle size={13} /> Caution
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
      </button>

      {isOpen && (
        <div style={{
          padding: '0.75rem 1rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          background: 'rgba(8, 12, 22, 0.9)',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
          color: '#cbd5e1',
          lineHeight: 1.6,
        }}>
          {steps.map((step, idx) => {
            const isError = step.toLowerCase().includes('error') || step.toLowerCase().includes('fail');
            const isTool = step.toLowerCase().startsWith('tool');
            const isCritic = step.toLowerCase().startsWith('critic');

            let dotColor = '#94a3b8';
            if (isError) dotColor = '#f43f5e';
            else if (isCritic) dotColor = '#10b981';
            else if (isTool) dotColor = '#38bdf8';

            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', marginBottom: '0.4rem' }}>
                <span style={{ color: dotColor, marginTop: '2px' }}>●</span>
                <span style={{ wordBreak: 'break-all', color: isError ? '#fca5a5' : isCritic ? '#86efac' : '#cbd5e1' }}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
