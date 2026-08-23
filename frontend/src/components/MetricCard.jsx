import React from 'react';

export default function MetricCard({ title, value, subtitle, icon: Icon, color = 'primary', glow = false }) {
  const colorMap = {
    primary: {
      text: '#818cf8',
      bg: 'rgba(99, 102, 241, 0.15)',
      border: 'rgba(99, 102, 241, 0.3)',
    },
    cyan: {
      text: '#22d3ee',
      bg: 'rgba(6, 182, 212, 0.15)',
      border: 'rgba(6, 182, 212, 0.3)',
    },
    emerald: {
      text: '#34d399',
      bg: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.3)',
    },
    amber: {
      text: '#fbbf24',
      bg: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.3)',
    },
    rose: {
      text: '#f43f5e',
      bg: 'rgba(244, 63, 94, 0.15)',
      border: 'rgba(244, 63, 94, 0.3)',
    },
  };

  const scheme = colorMap[color] || colorMap.primary;

  return (
    <div className={`glass-card ${glow ? 'glow' : ''}`} style={{ padding: '1.4rem 1.6rem', position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.8rem' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {title}
        </span>
        {Icon && (
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 'var(--radius-sm)',
            background: scheme.bg,
            border: `1px solid ${scheme.border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: scheme.text,
          }}>
            <Icon size={20} />
          </div>
        )}
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-heading)', color: 'var(--text-primary)', lineHeight: 1.1 }}>
        {value}
      </div>
      {subtitle && (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}
