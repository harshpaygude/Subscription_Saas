interface WizardNavigationProps {
  current: number;
  total: number;
}

export function WizardNavigation({ current, total }: WizardNavigationProps) {
  return (
    <div className="sh-wizard-navigation" aria-label={`Step ${current} of ${total}`}>
      {Array.from({ length: total }, (_, index) => (
        <span key={index} className={index + 1 <= current ? "active" : ""} />
      ))}
    </div>
  );
}
