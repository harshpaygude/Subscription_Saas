import {
  BriefcaseBusiness,
  Cloud,
  Code2,
  CreditCard,
  GitBranch,
  Bot,
  Globe2,
  MessageSquare,
  Puzzle,
  ServerCog,
} from "lucide-react";

interface ProviderIconProps {
  icon: string;
  size?: number;
}

export function ProviderIcon({ icon, size = 22 }: ProviderIconProps) {
  const iconProps = { size, strokeWidth: 1.8 };
  switch (icon) {
    case "aws":
      return <Cloud {...iconProps} />;
    case "azure":
      return <ServerCog {...iconProps} />;
    case "gcp":
      return <Globe2 {...iconProps} />;
    case "microsoft":
      return <BriefcaseBusiness {...iconProps} />;
    case "google":
      return <Globe2 {...iconProps} />;
    case "slack":
      return <MessageSquare {...iconProps} />;
    case "github":
      return <GitBranch {...iconProps} />;
    case "stripe":
      return <CreditCard {...iconProps} />;
    case "openai":
    case "anthropic":
    case "gemini":
      return <Bot {...iconProps} />;
    case "gitlab":
      return <Code2 {...iconProps} />;
    case "custom":
      return <Puzzle {...iconProps} />;
    default:
      return <Code2 {...iconProps} />;
  }
}
