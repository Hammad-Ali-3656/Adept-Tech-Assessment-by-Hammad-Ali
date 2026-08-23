import React, { useState, useEffect } from 'react';
import { 
  Users, 
  TrendingDown, 
  AlertOctagon, 
  Target, 
  ArrowUpRight, 
  Sparkles,
  Layers,
  ArrowRight,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import MetricCard from '../components/MetricCard';
import RiskBadge from '../components/RiskBadge';
import { fetchStats, fetchSegments, fetchCustomers } from '../services/api';

export default function DashboardPage({ onNavigateTab, onSelectCustomer }) {
  const [stats, setStats] = useState(null);
  const [contractSegments, setContractSegments] = useState([]);
  const [internetSegments, setInternetSegments] = useState([]);
  const [topAtRisk, setTopAtRisk] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [statsData, contractData, internetData, custData] = await Promise.all([
          fetchStats(),
          fetchSegments('Contract'),
          fetchSegments('InternetService'),
          fetchCustomers({ limit: 5, riskBand: 'high', sortBy: 'model_risk', order: 'desc' })
        ]);
        setStats(statsData);
        setContractSegments(contractData.data || []);
        setInternetSegments(internetData.data || []);
        setTopAtRisk(custData.customers || []);
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const riskPieData = stats?.risk_tiers ? [
    { name: 'High Risk (≥66%)', value: stats.risk_tiers.high, color: '#f43f5e' },
    { name: 'Medium Risk (33-65%)', value: stats.risk_tiers.medium, color: '#f59e0b' },
    { name: 'Low Risk (<33%)', value: stats.risk_tiers.low, color: '#10b981' },
  ] : [];

  return (
    <div className="page-wrapper animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.2rem 0.6rem', borderRadius: 'var(--radius-full)', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', color: '#818cf8', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            <Sparkles size={12} /> Real-time Customer Intelligence
          </div>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.03em' }}>
            Executive <span className="text-gradient">Retention Dashboard</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '0.2rem' }}>
            Live behavioral analytics and machine learning risk predictions across 7,043 telecom subscribers.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            className="btn btn-secondary"
            onClick={() => onNavigateTab('whatif')}
          >
            <Layers size={16} /> Run What-If Sandbox
          </button>
          <button 
            className="btn btn-primary"
            onClick={() => onNavigateTab('chat')}
          >
            <Sparkles size={16} /> Ask AI Analyst
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <MetricCard
          title="Total Subscribers"
          value={stats?.total_customers ? stats.total_customers.toLocaleString() : '7,043'}
          subtitle="Cleaned customer cohort"
          icon={Users}
          color="primary"
        />
        <MetricCard
          title="Observed Churn Rate"
          value={stats?.churn_rate ? `${(stats.churn_rate * 100).toFixed(1)}%` : '26.5%'}
          subtitle={`${stats?.churned_count?.toLocaleString() || '1,869'} churned accounts`}
          icon={TrendingDown}
          color="rose"
        />
        <MetricCard
          title="High-Risk Accounts"
          value={stats?.risk_tiers?.high ? stats.risk_tiers.high.toLocaleString() : '1,714'}
          subtitle="Model probability ≥ 66%"
          icon={AlertOctagon}
          color="amber"
          glow={true}
        />
        <MetricCard
          title="Model PR-AUC"
          value={stats?.model?.pr_auc ? stats.model.pr_auc.toFixed(3) : '0.658'}
          subtitle="ROC-AUC 0.843 · F₂-Optimal"
          icon={Target}
          color="cyan"
        />
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Contract Type Retention */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Churn Rate by Contract Type</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Long-term commitments dramatically lower defection</p>
            </div>
            <span className="badge badge-neutral">15x drop</span>
          </div>

          <div style={{ height: 260, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={contractSegments} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="Contract" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip 
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  formatter={(val) => [`${(Number(val) * 100).toFixed(1)}%`, 'Churn Rate']}
                />
                <Bar dataKey="churn_rate" radius={[6, 6, 0, 0]}>
                  {contractSegments.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#f43f5e' : index === 1 ? '#f59e0b' : '#10b981'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Distribution Breakdown */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Subscriber Risk Tier Breakdown</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Segmented by model calibrated churn probability</p>
            </div>
            <span className="badge badge-medium">Actionable</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', height: 260 }}>
            <div style={{ flex: 1, height: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskPieData}
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {riskPieData.map((entry, index) => (
                      <Cell key={`pie-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                    formatter={(val) => [`${Number(val).toLocaleString()} subscribers`, 'Count']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ width: '180px', display: 'flex', flexDirection: 'column', gap: '0.8rem', fontSize: '0.8rem' }}>
              {riskPieData.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: item.color }}></div>
                  <div>
                    <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.value.toLocaleString()}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{item.name}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Top At-Risk Accounts Table */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Priority Retention Targets</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Subscribers with the highest model-predicted probability of defection</p>
          </div>
          <button 
            className="btn btn-secondary" 
            style={{ fontSize: '0.78rem', padding: '0.4rem 0.8rem' }}
            onClick={() => onNavigateTab('customers')}
          >
            View All Customers <ArrowRight size={14} />
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Customer ID</th>
                <th style={{ padding: '0.75rem 1rem' }}>Contract</th>
                <th style={{ padding: '0.75rem 1rem' }}>Internet</th>
                <th style={{ padding: '0.75rem 1rem' }}>Tenure</th>
                <th style={{ padding: '0.75rem 1rem' }}>Monthly Fee</th>
                <th style={{ padding: '0.75rem 1rem' }}>Model Risk</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {topAtRisk.map((c) => (
                <tr key={c.customerID} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}>
                  <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#f8fafc' }}>
                    {c.customerID}
                  </td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>{c.Contract}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>{c.InternetService}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>{c.tenure} mo</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>${Number(c.MonthlyCharges).toFixed(2)}</td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    <RiskBadge score={c.model_risk} band={c.risk_band} />
                  </td>
                  <td style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>
                    <button
                      className="btn btn-cyan"
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                      onClick={() => {
                        onSelectCustomer(c.customerID);
                        onNavigateTab('whatif');
                      }}
                    >
                      What-If Sandbox <ArrowUpRight size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
