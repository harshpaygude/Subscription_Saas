interface Props {
  step: number;
  total: number;
  steps: string[];
}

export function OnboardingProgress({ step, total, steps }: Props) {
  return (
    <div className="ob-progress">
      <div className="ob-progress-bar-wrap">
        <div className="ob-progress-bar" style={{ width: `${(step / total) * 100}%` }} />
      </div>
      <div className="ob-progress-steps">
        {steps.map((label, i) => (
          <div
            key={label}
            className={`ob-step ${i + 1 < step ? "ob-step-done" : ""} ${i + 1 === step ? "ob-step-active" : ""}`}
          >
            <div className="ob-step-dot">
              {i + 1 < step ? (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <span>{i + 1}</span>
              )}
            </div>
            <span className="ob-step-label">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
