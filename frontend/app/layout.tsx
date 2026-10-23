import type { Metadata } from "next";
import "./globals.css";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

export const metadata: Metadata = {
  title: "UniSora",
  description: "Subscription Management Platform",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}<ThemeToggle /></body>
    </html>
  );
}
