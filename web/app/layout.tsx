import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "Market-Relative Forecast Analytics",
  description: "Prediction market forecast and trade journal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <nav className="nav">
            <div className="brand">Market-Relative Forecast Analytics</div>
            <Link href="/">Dashboard</Link>
            <Link href="/markets">Markets</Link>
            <Link href="/markets/new">New Market</Link>
            <Link href="/positions">Positions</Link>
            <Link href="/bankroll">Bankroll</Link>
            <Link href="/settings/export">Export</Link>
            <Link href="/methodology">Methodology</Link>
          </nav>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}

