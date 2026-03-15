import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Research Copilot",
  description: "A lightweight workspace to support investment research workflows."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
