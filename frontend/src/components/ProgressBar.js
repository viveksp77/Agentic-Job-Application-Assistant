import React from 'react';

export default function ProgressBar({ steps, currentStep }) {
  const pct = Math.round((currentStep / steps.length) * 100);

  return (
    <div className="progress-wrap">
      <div className="progress-header">
        <span className="progress-title">⚡ Agent running...</span>
        <span className="progress-count">{currentStep}/{steps.length} steps</span>
      </div>

      <div className="progress-bar-bg">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>

      <div className="progress-steps">
        {steps.map((step, i) => {
          const done = i < currentStep;
          const active = i === currentStep;
          return (
            <div
              key={step}
              className={`progress-step ${done ? 'done' : ''} ${active ? 'active' : ''}`}
            >
              <div className="step-dot" />
              <span>{done ? '✓ ' : active ? '→ ' : ''}{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}