interface ConnectionStatusProps {
  status: string;
}

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  return <span className="sh-status">{status}</span>;
}
