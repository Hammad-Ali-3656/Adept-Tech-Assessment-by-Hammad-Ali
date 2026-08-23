import React from 'react';
import { 
  LayoutDashboard, 
  BotMessageSquare, 
  Users, 
  SlidersHorizontal, 
  UserPlus, 
  Cpu, 
  Sparkles, 
  ShieldCheck,
  TrendingDown
} from 'lucide-react';

export default function Sidebar({ activeTab, onSelectTab, stats }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null },
    { id: 'chat', label: 'AI Analyst Chat', icon: BotMessageSquare, badge: 'Agent' },
    { id: 'customers', label: 'Customer Explorer', icon: Users, badge: stats?.total_customers ? `${stats.total_customers.toLocaleString()}` : null },
    { id: 'whatif', label: 'What-If Simulator', icon: SlidersHorizontal, badge: 'Sandbox' },
    { id: 'hypothetical', label: 'Score New Customer', icon: UserPlus, badge: null },
    { id: 'model', label: 'Model Intelligence', icon: Cpu, badge: 'F₂-Tuned' },
  ];

  return (
    <aside style={{
      width: '270px',
      minWidth: '270px',
      height: '100vh',
      background: 'rgba(11, 15, 25, 0.95)',
      backdropFilter: 'blur(20px)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      padding: '1.5rem 1rem 1.25rem',
      zIndex: 20,
    }}>
      {/* Top Section: Brand */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.25rem 0.5rem 1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            boxShadow: '0 4px 16px rgba(99, 102, 241, 0.4)',
          }}>
            <TrendingDown size={20} strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              Churn<span style={{ color: 'var(--cyan)' }}>Analyst</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '2px' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }}></span>
              Autonomous Retention AI
            </div>
          </div>
        </div>

        {/* Navigation items */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginTop: '1.25rem' }}>
          <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, padding: '0 0.5rem 0.4rem', letterSpacing: '0.06em' }}>
            Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '0.65rem 0.8rem',
                  borderRadius: 'var(--radius-sm)',
                  border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                  background: isActive ? 'linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(6, 182, 212, 0.05) 100%)' : 'transparent',
                  color: isActive ? '#f8fafc' : 'var(--text-secondary)',
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                    e.currentTarget.style.color = '#fff';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
                  <Icon size={18} color={isActive ? '#818cf8' : '#94a3b8'} strokeWidth={isActive ? 2.2 : 1.8} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '0.15rem 0.45rem',
                    borderRadius: 'var(--radius-full)',
                    background: isActive ? 'rgba(99, 102, 241, 0.3)' : 'rgba(255, 255, 255, 0.06)',
                    color: isActive ? '#c7d2fe' : 'var(--text-muted)',
                  }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Section: Model Specs badge */}
      <div className="glass-panel" style={{ padding: '0.85rem', background: 'rgba(15, 23, 42, 0.5)', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem', color: '#818cf8', fontSize: '0.75rem', fontWeight: 600 }}>
          <Sparkles size={13} />
          <span>Active ML Engine</span>
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
          Gradient Boosting · PR-AUC {stats?.model?.pr_auc ? stats.model.pr_auc.toFixed(3) : '0.658'}
        </div>
        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
          Decision threshold: {stats?.model?.threshold ? stats.model.threshold.toFixed(3) : '0.105'} (F₂)
        </div>
      </div>
    </aside>
  );
}
