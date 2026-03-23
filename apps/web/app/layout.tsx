import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "QuantumValue Terminal",
  description: "Financial archaeology workspace for long-horizon fundamental analysis.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-abyss text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
