import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastSeries } from "@/types";

export default function ForecastChart({ series }: { series: ForecastSeries }) {
  const data = series.points.map((p) => ({
    date: new Date(p.date).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }),
    low: Math.round(p.low),
    mid: Math.round(p.mid),
    high: Math.round(p.high),
  }));

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`band-${series.product_ref}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1a2745" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={{ stroke: "#1a2745" }}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a",
              border: "1px solid #1a2745",
              borderRadius: 12,
              fontSize: 12,
            }}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Area
            type="monotone"
            dataKey="high"
            stroke="transparent"
            fill={`url(#band-${series.product_ref})`}
            name="Haut"
          />
          <Area
            type="monotone"
            dataKey="low"
            stroke="transparent"
            fill={`url(#band-${series.product_ref})`}
            name="Bas"
          />
          <Area
            type="monotone"
            dataKey="mid"
            stroke="#818cf8"
            strokeWidth={2}
            fill="transparent"
            dot={false}
            name="Prévision"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
