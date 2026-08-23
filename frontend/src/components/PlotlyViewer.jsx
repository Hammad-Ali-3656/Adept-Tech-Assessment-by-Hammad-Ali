import React, { Suspense, lazy } from 'react';

// Lazy-load Plotly component to optimize bundle size
const Plot = lazy(() => import('react-plotly.js'));

export default function PlotlyViewer({ figureJson }) {
  if (!figureJson) return null;

  try {
    const data = figureJson.data || [];
    const layout = {
      ...(figureJson.layout || {}),
      autosize: true,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#cbd5e1', family: 'Plus Jakarta Sans, sans-serif' },
      margin: { l: 40, r: 20, t: 40, b: 40 },
    };

    return (
      <div style={{
        width: '100%',
        minHeight: '340px',
        background: 'rgba(15, 23, 42, 0.4)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '0.5rem',
        marginTop: '0.75rem',
        overflow: 'hidden',
      }}>
        <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>Rendering chart visualization…</div>}>
          <Plot
            data={data}
            layout={layout}
            useResizeHandler={true}
            style={{ width: '100%', height: '100%' }}
            config={{ responsive: true, displayModeBar: false }}
          />
        </Suspense>
      </div>
    );
  } catch (e) {
    return <div style={{ color: 'var(--rose)', fontSize: '0.8rem', padding: '0.5rem' }}>Failed to render chart: {String(e)}</div>;
  }
}
