import React from 'react';

export const MetricCard = ({ title, value, subtext, subtitle, icon, trend, color = 'blue' }) => {
  const colorMap = {
    blue: { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.25)' },
    emerald: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.25)' },
    amber: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.25)' },
    purple: { bg: 'rgba(139, 92, 246, 0.15)', text: '#c084fc', border: 'rgba(139, 92, 246, 0.25)' },
    rose: { bg: 'rgba(244, 63, 94, 0.15)', text: '#fb7185', border: 'rgba(244, 63, 94, 0.25)' },
  };

  const scheme = colorMap[color] || colorMap.blue;
  const description = subtext || subtitle;

  const renderIcon = () => {
    if (!icon) return null;
    if (React.isValidElement(icon)) {
      return icon;
    }
    if (typeof icon === 'function' || (typeof icon === 'object' && icon !== null)) {
      const IconComponent = icon;
      return <IconComponent size={20} />;
    }
    return null;
  };

  return (
    <div className="metric-card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{title}</span>
        {icon && (
          <div
            className="metric-card-icon"
            style={{ background: scheme.bg, color: scheme.text, border: `1px solid ${scheme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            {renderIcon()}
          </div>
        )}
      </div>

      <div className="metric-value">{value}</div>

      {(description || trend) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', marginTop: '0.2rem' }}>
          {trend && (
            <span
              style={{
                color: trend.startsWith('+') ? '#34d399' : '#fb7185',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              {trend}
            </span>
          )}
          {description && <span style={{ color: 'var(--text-muted)' }}>{description}</span>}
        </div>
      )}
    </div>
  );
};

export default MetricCard;
