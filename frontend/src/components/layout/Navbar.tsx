import Link from "next/link";
import { Activity } from "lucide-react";

const navLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/predictions", label: "Predictions" },
];

const leagueLinks = [
  { href: "/leagues/PL", label: "Premier League" },
  { href: "/leagues/PD", label: "La Liga" },
  { href: "/leagues/BL1", label: "Bundesliga" },
  { href: "/leagues/SA", label: "Serie A" },
];

export function Navbar() {
  return (
    <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-7xl flex h-16 items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2 font-bold text-xl text-blue-400">
          <Activity className="h-5 w-5" />
          OctoPredict
        </Link>

        <div className="flex items-center gap-6 text-sm">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-slate-300 hover:text-white transition-colors"
            >
              {link.label}
            </Link>
          ))}

          <div className="relative group">
            <button className="text-slate-300 hover:text-white transition-colors">
              Leagues ▾
            </button>
            <div className="absolute right-0 mt-2 w-44 bg-slate-800 border border-slate-700 rounded-md shadow-lg hidden group-hover:block z-50">
              {leagueLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="block px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
