import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "Market-Relative Forecast Analytics",
  description: "Prediction market forecast and trade journal",
  icons: {
    icon: "/brand/app-icon.png",
    shortcut: "/brand/app-icon.png",
    apple: "/brand/app-icon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <nav className="nav">
            <div className="brand">
              <img src="/brand/app-icon.svg" alt="" className="brand-icon" />
              <span>Market-Relative Forecast Analytics</span>
            </div>
            <Link href="/">Dashboard</Link>
            <Link href="/settings/kalshi">Sync Kalshi</Link>
            <Link href="/needs-forecast">Missing Forecasts</Link>
            <Link href="/markets">Markets</Link>
            <Link href="/positions">Positions</Link>
            <Link href="/bankroll">Bankroll</Link>
            <Link href="/review">Review</Link>
            <Link href="/settings/export">Export</Link>
            <Link href="/methodology">Methodology</Link>
          </nav>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
