import { faAws } from "@fortawesome/free-brands-svg-icons";
import type { IconDefinition } from "@fortawesome/fontawesome-common-types";
import {
  siAnthropic,
  siGithub,
  siGitlab,
  siGoogle,
  siGooglecloud,
  siGooglegemini,
  siOpenai,
  siSlack,
  siStripe,
} from "simple-icons";

interface ProviderLogoProps {
  icon: string;
  size?: number;
}

const simpleIcons = {
  anthropic: siAnthropic,
  github: siGithub,
  gitlab: siGitlab,
  google: siGoogle,
  gcp: siGooglecloud,
  gemini: siGooglegemini,
  openai: siOpenai,
  slack: siSlack,
  stripe: siStripe,
};

const fontAwesomeIcons: Record<string, IconDefinition | undefined> = {
  aws: faAws,
};

function AzureLogo({ size }: { size: number }) {
  return <svg width={size} height={size} viewBox="0 0 256 256" aria-hidden="true" focusable="false"><defs><linearGradient id="azure-primary" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#114a8b" /><stop offset="1" stopColor="#0669bc" /></linearGradient><linearGradient id="azure-secondary" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#3ccbf4" /><stop offset="1" stopColor="#2892df" /></linearGradient></defs><path d="M89.158 18.266h69.238L86.523 231.224a11.041 11.041 0 0 1-10.461 7.51H22.179a11.023 11.023 0 0 1-10.445-14.548l66.963-198.41a11.04 11.04 0 0 1 10.461-7.51Z" fill="url(#azure-primary)" /><path d="M189.77 161.104H79.976a5.083 5.083 0 0 0-3.468 8.8l70.552 65.847a11.091 11.091 0 0 0 7.567 2.983h62.167Z" fill="#0078d4" /><path d="M177.592 25.764a11.023 11.023 0 0 0-10.444-7.498H89.984a11.024 11.024 0 0 1 10.445 7.498l66.967 198.421a11.024 11.024 0 0 1-10.445 14.549h77.164a11.024 11.024 0 0 0 10.444-14.549Z" fill="url(#azure-secondary)" /></svg>;
}

function MicrosoftLogo({ size }: { size: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 2h9.5v9.5H2z" fill="#f35325" /><path d="M12.5 2H22v9.5h-9.5z" fill="#81bc06" /><path d="M2 12.5h9.5V22H2z" fill="#05a6f0" /><path d="M12.5 12.5H22V22h-9.5z" fill="#ffba08" /></svg>;
}

export function ProviderLogo({ icon, size = 22 }: ProviderLogoProps) {
  const simpleIcon = simpleIcons[icon as keyof typeof simpleIcons];
  if (simpleIcon) return <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill={`#${simpleIcon.hex}`}><path d={simpleIcon.path} /></svg>;
  if (icon === "azure") return <AzureLogo size={size} />;
  if (icon === "microsoft") return <MicrosoftLogo size={size} />;

  const fontAwesomeIcon = fontAwesomeIcons[icon];
  if (fontAwesomeIcon) {
    const [width, height, , , path] = fontAwesomeIcon.icon;
    const paths = Array.isArray(path) ? path : [path];
    return <svg width={size} height={size} viewBox={`0 0 ${width} ${height}`} aria-hidden="true" focusable="false">{paths.map((item, index) => <path key={index} d={item} fill={icon === "aws" ? "#ff9900" : "#737373"} />)}</svg>;
  }

  return <span aria-hidden="true" className="hub-provider-logo-fallback">{icon.slice(0, 1).toUpperCase()}</span>;
}
