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
            <Link href="/">Home</Link>
            <Link href="/settings/kalshi">Sync Kalshi</Link>
            <Link href="/needs-forecast">Needs Forecast</Link>
            <Link href="/markets">Markets</Link>
            <Link href="/positions">Positions</Link>
            <Link href="/settings/export">Export</Link>
            <Link href="/methodology">Methodology</Link>
          </nav>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
