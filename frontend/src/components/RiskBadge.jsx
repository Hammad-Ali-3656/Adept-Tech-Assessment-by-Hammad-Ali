import React from 'react';

export default function RiskBadge({ band, score }) {
  const normalizedBand = (band || '').toLowerCase();
  let badgeClass = 'badge-neutral';
  
  if (normalizedBand === 'high' || score >= 0.66) {
    badgeClass = 'badge-high';
  } else if (normalizedBand === 'medium' || (score >= 0.33 && score < 0.66)) {
    badgeClass = 'badge-medium';
  } else if (normalizedBand === 'low' || (score !== undefined && score < 0.33)) {
    badgeClass = 'badge-low';
  }

  const label = band || (score !== undefined ? (score >= 0.66 ? 'High' : score >= 0.33 ? 'Medium' : 'Low') : 'Unknown');

  return (
    <span className={`badge ${badgeClass}`}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }}></span>
      {label} {score !== undefined ? `(${(score * 100).toFixed(1)}%)` : ''}
    </span>
  );
}
