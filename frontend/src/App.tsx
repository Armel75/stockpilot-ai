import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  Crosshair,
  Settings2,
  Boxes,
} from "lucide-react";
import clsx from "clsx";
import TopBar from "@/components/layout/TopBar";
import Pilotage from "@/pages/Pilotage";
import Forecasts from "@/pages/Forecasts";
import Products from "@/pages/Products";
import Accuracy from "@/pages/Accuracy";
import System from "@/pages/System";

const NAV = [
  { to: "/", label: "Pilotage", icon: LayoutDashboard, end: true },
  { to: "/previsions", label: "Prévisions", icon: TrendingUp },
  { to: "/produits", label: "Produits", icon: Package },
  { to: "/precision", label: "Précision", icon: Crosshair },
  { to: "/systeme", label: "Système", icon: Settings2 },
];

export default function App() {
  return (
    <div className="min-h-screen flex bg-ink-950">
      <aside className="hidden lg:flex w-64 flex-col border-r border-ink-700/60 bg-ink-900/50 sticky top-0 h-screen">
        <div className="flex items-center gap-3 px-5 py-6">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-glow">
            <Boxes className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-white font-bold leading-tight">StockPilot</p>
            <p className="text-xs text-slate-400">AI · Stocks & Ventes</p>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-ink-800 border border-transparent"
                )
              }
            >
              <item.icon className="h-4.5 w-4.5 h-5 w-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-[11px] text-slate-500 leading-relaxed border-t border-ink-700/60">
          Agent de pilotage — prévisions déterministes + narration DeepSeek.
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Pilotage />} />
            <Route path="/previsions" element={<Forecasts />} />
            <Route path="/produits" element={<Products />} />
            <Route path="/precision" element={<Accuracy />} />
            <Route path="/systeme" element={<System />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
