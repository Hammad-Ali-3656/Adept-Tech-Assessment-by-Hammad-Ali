// Frontend API service for Churn Analyst Agent

const API_BASE = '/api';

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`Failed to load stats: ${res.statusText}`);
  return res.json();
}

export async function fetchSegments(by = 'Contract') {
  const res = await fetch(`${API_BASE}/segments?by=${encodeURIComponent(by)}`);
  if (!res.ok) throw new Error(`Failed to load segments: ${res.statusText}`);
  return res.json();
}

export async function fetchCustomers({ page = 1, limit = 15, search = '', riskBand = '', contract = '', sortBy = 'model_risk', order = 'desc' } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
    sort_by: sortBy,
    order: order,
  });
  if (search) params.append('search', search);
  if (riskBand) params.append('risk_band', riskBand);
  if (contract) params.append('contract', contract);

  const res = await fetch(`${API_BASE}/customers?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load customers: ${res.statusText}`);
  return res.json();
}

export async function fetchCustomer(customerId) {
  const res = await fetch(`${API_BASE}/customer/${encodeURIComponent(customerId)}`);
  if (!res.ok) throw new Error(`Failed to load customer ${customerId}: ${res.statusText}`);
  return res.json();
}

export async function runWhatIf(customerId, overrides) {
  const res = await fetch(`${API_BASE}/what-if`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId, overrides }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'What-If analysis failed');
  }
  return res.json();
}

export async function predictHypothetical(features) {
  const res = await fetch(`${API_BASE}/predict-hypothetical`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ features }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Hypothetical prediction failed');
  }
  return res.json();
}

export async function sendChatMessage(question, clearHistory = false) {
  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, clear_history: clearHistory }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
      throw new Error(err.detail || `Server returned status ${res.status}`);
    }
    return res.json();
  } catch (err) {
    throw new Error(err.message || 'Chat request failed');
  }
}

export async function fetchModelCard() {
  const res = await fetch(`${API_BASE}/model-card`);
  if (!res.ok) throw new Error(`Failed to load model card: ${res.statusText}`);
  return res.json();
}
