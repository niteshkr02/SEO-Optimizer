import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO Optimizer — Evidence-Based Technical SEO Diagnosis",
  description:
    "Deterministic, zero-trust technical SEO diagnosis and verifiable code resolution platform. Auditing 20 Core SEO rules with mathematical provenance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}

