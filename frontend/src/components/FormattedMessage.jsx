import React from 'react';

/**
 * Lightweight formatted message renderer that converts markdown-like text
 * (bold, headers, bullets, numbers, code) into styled React elements.
 */
export default function FormattedMessage({ content }) {
  if (!content) return null;

  const lines = content.split('\n');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.92rem', lineHeight: 1.65, color: '#f8fafc' }}>
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} style={{ height: '0.3rem' }} />;
        }

        // Header 3: ### Title
        if (trimmed.startsWith('### ')) {
          return (
            <h4 key={idx} style={{ fontSize: '1.05rem', fontWeight: 700, color: '#e0e7ff', marginTop: '0.4rem', marginBottom: '0.1rem' }}>
              {formatInline(trimmed.substring(4))}
            </h4>
          );
        }

        // Header 2 or 1: ## Title or # Title
        if (trimmed.startsWith('## ') || trimmed.startsWith('# ')) {
          return (
            <h3 key={idx} style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.5rem', marginBottom: '0.2rem' }}>
              {formatInline(trimmed.replace(/^#+\s*/, ''))}
            </h3>
          );
        }

        // Bullet point: * or -
        if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
          return (
            <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', paddingLeft: '0.4rem' }}>
              <span style={{ color: '#818cf8', fontWeight: 'bold', lineHeight: 1.4 }}>•</span>
              <span style={{ flex: 1 }}>{formatInline(trimmed.substring(2))}</span>
            </div>
          );
        }

        // Numbered list: 1. 2. 3.
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
        if (numMatch) {
          return (
            <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', paddingLeft: '0.4rem' }}>
              <span style={{ color: '#06b6d4', fontWeight: 700, fontSize: '0.85rem', minWidth: '1.2rem' }}>{numMatch[1]}.</span>
              <span style={{ flex: 1 }}>{formatInline(numMatch[2])}</span>
            </div>
          );
        }

        // Standard Paragraph
        return (
          <p key={idx} style={{ margin: 0 }}>
            {formatInline(line)}
          </p>
        );
      })}
    </div>
  );
}

function formatInline(text) {
  // Replace bold **text** and code `text`
  const parts = [];
  let remaining = text;
  let key = 0;

  // Regex matching **bold**, `code`, or regular text
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let match;
  let lastIndex = 0;

  while ((match = regex.exec(text)) !== null) {
    // Push preceding text
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={key++} style={{ color: '#ffffff', fontWeight: 700 }}>
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={key++}
          style={{
            background: 'rgba(99, 102, 241, 0.15)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            borderRadius: 4,
            padding: '0.1rem 0.35rem',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.82rem',
            color: '#a5b4fc',
          }}
        >
          {token.slice(1, -1)}
        </code>
      );
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}
