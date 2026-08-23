import React, { useState, useEffect } from 'react';
import { Search, Filter, ArrowUpDown, ChevronLeft, ChevronRight, SlidersHorizontal, ArrowUpRight } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { fetchCustomers } from '../services/api';

export default function CustomerExplorerPage({ onNavigateTab, onSelectCustomer }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [riskBand, setRiskBand] = useState('');
  const [contract, setContract] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      const data = await fetchCustomers({
        page,
        limit: 15,
        search,
        riskBand,
        contract,
        sortBy: 'model_risk',
        order: 'desc',
      });
      setCustomers(data.customers || []);
      setTotalPages(data.total_pages || 1);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCustomers();
  }, [page, riskBand, contract]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadCustomers();
  };

  return (
    <div className="page-wrapper animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.75rem' }}>
        <div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>Customer Directory & Intelligence</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.2rem' }}>
            Browse and inspect all {totalCount.toLocaleString()} telecom accounts sorted by ML churn risk.
          </p>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-card" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', justifyContent: 'space-between' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: '1 1 280px', maxWidth: '400px' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 12 }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search Customer ID (e.g. 7590-VHVEG)..."
              style={{
                width: '100%',
                padding: '0.6rem 1rem 0.6rem 2.4rem',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 'var(--radius-sm)',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ padding: '0.6rem 1rem', fontSize: '0.8rem' }}>
            Search
          </button>
        </form>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            <Filter size={14} /> Filter:
          </div>

          <select
            value={riskBand}
            onChange={(e) => { setRiskBand(e.target.value); setPage(1); }}
            style={{
              padding: '0.55rem 0.9rem',
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 'var(--radius-sm)',
              color: '#cbd5e1',
              fontSize: '0.82rem',
              outline: 'none',
            }}
          >
            <option value="">All Risk Bands</option>
            <option value="high">High Risk (≥66%)</option>
            <option value="medium">Medium Risk (33-65%)</option>
            <option value="low">Low Risk (&lt;33%)</option>
          </select>

          <select
            value={contract}
            onChange={(e) => { setContract(e.target.value); setPage(1); }}
            style={{
              padding: '0.55rem 0.9rem',
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 'var(--radius-sm)',
              color: '#cbd5e1',
              fontSize: '0.82rem',
              outline: 'none',
            }}
          >
            <option value="">All Contracts</option>
            <option value="Month-to-month">Month-to-month</option>
            <option value="One year">One year</option>
            <option value="Two year">Two year</option>
          </select>
        </div>
      </div>

      {/* Customers Table */}
      <div className="glass-panel" style={{ padding: '1rem', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Customer ID</th>
                <th style={{ padding: '0.75rem 1rem' }}>Contract</th>
                <th style={{ padding: '0.75rem 1rem' }}>Internet</th>
                <th style={{ padding: '0.75rem 1rem' }}>Tenure</th>
                <th style={{ padding: '0.75rem 1rem' }}>Monthly Fee</th>
                <th style={{ padding: '0.75rem 1rem' }}>Total Spent</th>
                <th style={{ padding: '0.75rem 1rem' }}>Status</th>
                <th style={{ padding: '0.75rem 1rem' }}>Model Churn Risk</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.customerID} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}>
                  <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#f8fafc' }}>
                    {c.customerID}
                  </td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>{c.Contract}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>{c.InternetService}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>{c.tenure} mo</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>${Number(c.MonthlyCharges).toFixed(2)}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>${Number(c.TotalCharges).toFixed(2)}</td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    <span className={`badge ${c.Churn === 'Yes' ? 'badge-high' : 'badge-low'}`} style={{ fontSize: '0.68rem' }}>
                      {c.Churn === 'Yes' ? 'Churned' : 'Retained'}
                    </span>
                  </td>
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
                      <SlidersHorizontal size={13} /> Simulate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.25rem', padding: '0.5rem 0.5rem 0' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing page {page} of {totalPages} ({totalCount.toLocaleString()} accounts)
          </span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.78rem', opacity: page <= 1 ? 0.5 : 1 }}
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <button
              className="btn btn-secondary"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.78rem', opacity: page >= totalPages ? 0.5 : 1 }}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
