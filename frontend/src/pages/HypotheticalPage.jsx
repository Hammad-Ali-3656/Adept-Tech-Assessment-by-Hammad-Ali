import React, { useState } from 'react';
import { UserPlus, Sparkles, CheckCircle2, ShieldAlert, Layers } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { predictHypothetical } from '../services/api';

export default function HypotheticalPage() {
  const [formData, setFormData] = useState({
    tenure: 2,
    Contract: 'Month-to-month',
    InternetService: 'Fiber optic',
    MonthlyCharges: 75.0,
    TotalCharges: 150.0,
    TechSupport: 'No',
    OnlineSecurity: 'No',
    PaperlessBilling: 'Yes',
    PaymentMethod: 'Electronic check',
    SeniorCitizen: 'No',
    Partner: 'No',
    Dependents: 'No',
    PhoneService: 'Yes',
    MultipleLines: 'No',
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await predictHypothetical(formData);
      setResult(res);
    } catch (err) {
      alert(`Prediction failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="page-wrapper animate-fade-in" style={{ maxWidth: '1000px' }}>
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#818cf8', fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.4rem' }}>
          <UserPlus size={14} /> New Lead & Custom Prospect Scoring
        </div>
        <h2 style={{ fontSize: '2.2rem', fontWeight: 800 }}>Score Hypothetical Customer</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
          Simulate any arbitrary combination of subscriber attributes to predict defection likelihood.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '2rem' }}>
        {/* Input Form */}
        <form onSubmit={handleSubmit} className="glass-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.75rem' }}>
            Customer Profile Parameters
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {/* Tenure */}
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Tenure (Months):
              </label>
              <input
                type="number"
                min="0"
                max="72"
                value={formData.tenure}
                onChange={(e) => handleChange('tenure', parseInt(e.target.value) || 0)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.8rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>

            {/* Monthly Charges */}
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Monthly Charges ($):
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.MonthlyCharges}
                onChange={(e) => handleChange('MonthlyCharges', parseFloat(e.target.value) || 0)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.8rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {/* Contract */}
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Contract:
              </label>
              <select
                value={formData.Contract}
                onChange={(e) => handleChange('Contract', e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.8rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="Month-to-month">Month-to-month</option>
                <option value="One year">One year</option>
                <option value="Two year">Two year</option>
              </select>
            </div>

            {/* Internet Service */}
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Internet Service:
              </label>
              <select
                value={formData.InternetService}
                onChange={(e) => handleChange('InternetService', e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.8rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="Fiber optic">Fiber optic</option>
                <option value="DSL">DSL</option>
                <option value="No">No Internet</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {/* Tech Support */}
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Tech Support:
              </label>
              <select
                value={formData.TechSupport}
                onChange={(e) => handleChange('TechSupport', e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.8rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="No">No</option>
                <option value="Yes">Yes</option>
              </select>
            </div>

            {/* Online Security */}
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Online Security:
              </label>
              <select
                value={formData.OnlineSecurity}
                onChange={(e) => handleChange('OnlineSecurity', e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.8rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="No">No</option>
                <option value="Yes">Yes</option>
              </select>
            </div>
          </div>

          {/* Payment Method */}
          <div>
            <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
              Payment Method:
            </label>
            <select
              value={formData.PaymentMethod}
              onChange={(e) => handleChange('PaymentMethod', e.target.value)}
              style={{
                width: '100%',
                padding: '0.55rem 0.8rem',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 'var(--radius-sm)',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              <option value="Electronic check">Electronic check</option>
              <option value="Credit card (automatic)">Credit card (automatic)</option>
              <option value="Bank transfer (automatic)">Bank transfer (automatic)</option>
              <option value="Mailed check">Mailed check</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem', fontSize: '0.9rem' }}
          >
            <Sparkles size={16} /> {loading ? 'Calculating risk…' : 'Score Hypothetical Profile'}
          </button>
        </form>

        {/* Prediction Output Card */}
        <div>
          {result ? (
            <div className="glass-card animate-fade-in" style={{ padding: '1.75rem', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Model Prediction
                </span>
                <RiskBadge score={result.risk_score} band={result.risk_band} />
              </div>

              <div style={{ textAlign: 'center', padding: '1.5rem 0', background: 'rgba(15, 23, 42, 0.7)', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>Predicted Churn Probability</div>
                <div style={{ fontSize: '3rem', fontWeight: 800, fontFamily: 'var(--font-heading)', color: result.risk_score >= 0.66 ? '#f43f5e' : result.risk_score >= 0.33 ? '#f59e0b' : '#10b981' }}>
                  {(result.risk_score * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  {result.risk_band} Risk Category
                </div>
              </div>

              <div style={{
                padding: '1rem',
                borderRadius: 'var(--radius-sm)',
                background: result.would_flag_as_churn ? 'rgba(244, 63, 94, 0.12)' : 'rgba(16, 185, 129, 0.12)',
                border: `1px solid ${result.would_flag_as_churn ? 'rgba(244, 63, 94, 0.25)' : 'rgba(16, 185, 129, 0.25)'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                fontSize: '0.85rem',
              }}>
                {result.would_flag_as_churn ? (
                  <>
                    <ShieldAlert size={20} color="#f43f5e" />
                    <div>
                      <strong style={{ color: '#fda4af' }}>Flagged for Retention Action</strong>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Exceeds F₂-optimal decision cutoff (10.5%)</div>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={20} color="#10b981" />
                    <div>
                      <strong style={{ color: '#a7f3d0' }}>Safe / Low Priority</strong>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Below retention decision threshold</div>
                    </div>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '3rem 2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Layers size={36} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Awaiting Parameters</h4>
              <p style={{ fontSize: '0.82rem', lineHeight: 1.5 }}>
                Fill out the profile on the left and click <strong>Score Hypothetical Profile</strong> to generate instantaneous model predictions.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
