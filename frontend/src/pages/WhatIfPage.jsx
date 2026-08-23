import React, { useState, useEffect } from 'react';
import { 
  SlidersHorizontal, 
  Search, 
  ArrowRight, 
  TrendingDown, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Zap,
  Sparkles,
  RefreshCw
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { fetchCustomer, runWhatIf } from '../services/api';

export default function WhatIfPage({ selectedCustomerId = '7590-VHVEG' }) {
  const [customerId, setCustomerId] = useState(selectedCustomerId);
  const [inputCustomerId, setInputCustomerId] = useState(selectedCustomerId);
  const [customerData, setCustomerData] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  
  // Overrides state for counterfactual simulation
  const [overrides, setOverrides] = useState({});
  const [simulationResult, setSimulationResult] = useState(null);

  useEffect(() => {
    if (customerId) {
      loadCustomer(customerId);
    }
  }, [customerId]);

  const loadCustomer = async (id) => {
    try {
      setLoading(true);
      const data = await fetchCustomer(id);
      setCustomerData(data.customer);
      setPrediction(data.prediction);
      
      // Initialize overrides with current values
      const initialOverrides = {
        Contract: data.customer.Contract,
        TechSupport: data.customer.TechSupport,
        OnlineSecurity: data.customer.OnlineSecurity,
        PaperlessBilling: data.customer.PaperlessBilling,
        PaymentMethod: data.customer.PaymentMethod,
        MonthlyCharges: Number(data.customer.MonthlyCharges),
      };
      setOverrides(initialOverrides);
      setSimulationResult(null);
    } catch (err) {
      alert(`Customer '${id}' not found. Please try another ID like 7590-VHVEG or 3668-QPYBK.`);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async (newOverrides = overrides) => {
    if (!customerId) return;
    try {
      setSimulating(true);
      const res = await runWhatIf(customerId, newOverrides);
      setSimulationResult(res);
    } catch (err) {
      console.error('What-If simulation failed:', err);
    } finally {
      setSimulating(false);
    }
  };

  const handleOverrideChange = (key, value) => {
    const updated = { ...overrides, [key]: value };
    setOverrides(updated);
    handleSimulate(updated);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (inputCustomerId.trim()) {
      setCustomerId(inputCustomerId.trim());
    }
  };

  const currentRisk = prediction?.risk_score || 0;
  const projectedRisk = simulationResult?.projected_risk !== undefined ? simulationResult.projected_risk : currentRisk;
  const riskDelta = projectedRisk - currentRisk;

  return (
    <div className="page-wrapper animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.75rem' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#06b6d4', fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.4rem' }}>
            <Zap size={14} /> Counterfactual Retention Sandbox
          </div>
          <h2 style={{ fontSize: '2.2rem', fontWeight: 800 }}>Interactive What-If Simulator</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            Test potential contract offers, service upgrades, and discounts to simulate real-time churn risk reductions.
          </p>
        </div>

        {/* Customer Lookup Form */}
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={inputCustomerId}
            onChange={(e) => setInputCustomerId(e.target.value)}
            placeholder="Enter Customer ID..."
            style={{
              padding: '0.6rem 0.9rem',
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 'var(--radius-sm)',
              color: '#fff',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
              outline: 'none',
              width: '180px',
            }}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: '0.6rem 0.9rem', fontSize: '0.8rem' }}>
            <Search size={14} /> Load
          </button>
        </form>
      </div>

      {loading ? (
        <div className="glass-panel" style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading customer telemetry & baseline attributions…
        </div>
      ) : customerData ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
          
          {/* Left: Simulation Controls & Baseline Profile */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Customer Summary Bar */}
            <div className="glass-card" style={{ padding: '1.25rem 1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Selected Subscriber</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#f8fafc' }}>
                    {customerData.customerID}
                  </div>
                </div>
                <RiskBadge score={prediction?.risk_score} band={prediction?.risk_band} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', fontSize: '0.82rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.75rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Tenure:</span> <strong style={{ color: '#fff' }}>{customerData.tenure} mo</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Internet:</span> <strong style={{ color: '#fff' }}>{customerData.InternetService}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Monthly Fee:</span> <strong style={{ color: '#fff' }}>${Number(customerData.MonthlyCharges).toFixed(2)}</strong>
                </div>
              </div>
            </div>

            {/* Retention Strategy Levers (Sliders & Selects) */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <SlidersHorizontal size={18} color="#818cf8" /> Retention Levers
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#06b6d4', fontWeight: 600 }}>Live Counterfactual Sandbox</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                {/* Lever 1: Contract Type */}
                <div>
                  <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                    Contract Commitment:
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                    {['Month-to-month', 'One year', 'Two year'].map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => handleOverrideChange('Contract', c)}
                        style={{
                          padding: '0.6rem 0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          border: overrides.Contract === c ? '1px solid #818cf8' : '1px solid rgba(255,255,255,0.08)',
                          background: overrides.Contract === c ? 'rgba(99, 102, 241, 0.25)' : 'rgba(15, 23, 42, 0.7)',
                          color: overrides.Contract === c ? '#fff' : 'var(--text-secondary)',
                          fontSize: '0.8rem',
                          fontWeight: overrides.Contract === c ? 700 : 500,
                          cursor: 'pointer',
                          transition: 'all 0.15s',
                        }}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Lever 2: Service Add-ons */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                      Tech Support:
                    </label>
                    <select
                      value={overrides.TechSupport || 'No'}
                      onChange={(e) => handleOverrideChange('TechSupport', e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.55rem 0.75rem',
                        background: 'rgba(15, 23, 42, 0.8)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 'var(--radius-sm)',
                        color: '#fff',
                        fontSize: '0.82rem',
                        outline: 'none',
                      }}
                    >
                      <option value="Yes">Yes (Add Support)</option>
                      <option value="No">No</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                      Online Security:
                    </label>
                    <select
                      value={overrides.OnlineSecurity || 'No'}
                      onChange={(e) => handleOverrideChange('OnlineSecurity', e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.55rem 0.75rem',
                        background: 'rgba(15, 23, 42, 0.8)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 'var(--radius-sm)',
                        color: '#fff',
                        fontSize: '0.82rem',
                        outline: 'none',
                      }}
                    >
                      <option value="Yes">Yes (Add Security)</option>
                      <option value="No">No</option>
                    </select>
                  </div>
                </div>

                {/* Lever 3: Payment Method */}
                <div>
                  <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                    Payment Method:
                  </label>
                  <select
                    value={overrides.PaymentMethod || customerData.PaymentMethod}
                    onChange={(e) => handleOverrideChange('PaymentMethod', e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.55rem 0.75rem',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 'var(--radius-sm)',
                      color: '#fff',
                      fontSize: '0.82rem',
                      outline: 'none',
                    }}
                  >
                    <option value="Electronic check">Electronic check</option>
                    <option value="Credit card (automatic)">Credit card (automatic)</option>
                    <option value="Bank transfer (automatic)">Bank transfer (automatic)</option>
                    <option value="Mailed check">Mailed check</option>
                  </select>
                </div>

                {/* Lever 4: Monthly Charges Slider */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.82rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Simulated Monthly Charges:</span>
                    <strong style={{ color: 'var(--cyan)' }}>${Number(overrides.MonthlyCharges || 0).toFixed(2)}/mo</strong>
                  </div>
                  <input
                    type="range"
                    min="18"
                    max="120"
                    step="1"
                    value={overrides.MonthlyCharges || 50}
                    onChange={(e) => handleOverrideChange('MonthlyCharges', parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--cyan)' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <span>$18.00 (Promo)</span>
                    <span>Baseline: ${Number(customerData.MonthlyCharges).toFixed(2)}</span>
                    <span>$120.00 (Max)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Real-Time Impact & Top Attribution Factors */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Before vs After Impact Card */}
            <div className="glass-card" style={{ padding: '1.5rem', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1.25rem' }}>
                Simulated Retention Impact
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1rem', alignItems: 'center', marginBottom: '1.5rem' }}>
                {/* Baseline Box */}
                <div style={{ padding: '1rem', background: 'rgba(15, 23, 42, 0.8)', borderRadius: 'var(--radius-sm)', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Current Baseline</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, fontFamily: 'var(--font-heading)', color: '#fda4af' }}>
                    {(currentRisk * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    {prediction?.risk_band} Tier
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ArrowRight size={22} color="var(--cyan)" />
                </div>

                {/* Projected Box */}
                <div style={{ padding: '1rem', background: 'rgba(6, 182, 212, 0.1)', borderRadius: 'var(--radius-sm)', textAlign: 'center', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
                  <div style={{ fontSize: '0.75rem', color: '#38bdf8', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Projected Risk</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, fontFamily: 'var(--font-heading)', color: '#34d399' }}>
                    {(projectedRisk * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#a7f3d0', marginTop: '0.2rem' }}>
                    {simulationResult?.projected_band || prediction?.risk_band} Tier
                  </div>
                </div>
              </div>

              {/* Net Risk Delta Badge */}
              <div style={{
                padding: '0.85rem 1rem',
                borderRadius: 'var(--radius-sm)',
                background: riskDelta < 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                border: `1px solid ${riskDelta < 0 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
                  {riskDelta <= 0 ? 'Projected Risk Reduction:' : 'Projected Risk Increase:'}
                </span>
                <span style={{
                  fontSize: '1.1rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  color: riskDelta <= 0 ? '#34d399' : '#f87171',
                }}>
                  {riskDelta <= 0 ? '' : '+'}{(riskDelta * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Top Local Risk Factors Attribution */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.4rem' }}>
                Customer Risk Drivers
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                Baseline-substitution feature attributions for customer {customerData.customerID}
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {prediction?.top_factors?.map((factor, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: 'rgba(15, 23, 42, 0.6)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.04)' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>{factor.feature}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Current value: {String(factor.value)}</div>
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      color: factor.impact > 0 ? '#fda4af' : '#a7f3d0',
                    }}>
                      {factor.impact > 0 ? `+${(factor.impact * 100).toFixed(1)}%` : `${(factor.impact * 100).toFixed(1)}%`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
