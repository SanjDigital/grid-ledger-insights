import { useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { VerifiedEvent } from "@/lib/mock-data";

interface YieldEfficiencyChartProps {
  events: VerifiedEvent[];
  currentSEC: number;
}

const LEAKAGE_THRESHOLD = 40;

export function YieldEfficiencyChart({ events, currentSEC }: YieldEfficiencyChartProps) {
  const chartData = useMemo(() => {
    return [...events]
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .map((e, i) => ({
        day: `C${i + 1}`,
        energy: e.kwh,
        yield_kg: e.yieldKg,
        tokenId: e.tokenId
      }));
  }, [events]);

  const enriched = useMemo(
    () =>
      chartData.map((d) => ({
        ...d,
        yieldHealthy: d.yield_kg >= LEAKAGE_THRESHOLD ? d.yield_kg : LEAKAGE_THRESHOLD,
        yieldLeakage: d.yield_kg < LEAKAGE_THRESHOLD ? d.yield_kg : LEAKAGE_THRESHOLD,
      })),
    [chartData],
  );

  const currentEfficiency = currentSEC > 0 ? (1 / currentSEC) : 0;
  // Variance from a nominal baseline of 0.040 kWh/kg (25 kg/kWh)
  const baselineEfficiency = 25; 
  const variance = baselineEfficiency > 0 ? ((currentEfficiency - baselineEfficiency) / baselineEfficiency) * 100 : 0;

  return (
    <div className="card-terminal animate-slide-up">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Yield Efficiency</h3>
          <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
            Production cycles energy vs. actual yield — correlation gap analysis
          </p>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm bg-sovereign" />
            Energy (kWh)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: "hsl(185,70%,50%)" }} />
            Yield (kg)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm bg-gap-detected" />
            Leakage
          </span>
        </div>
      </div>

      {/* Efficiency Metric Strip */}
      <div className="px-4 py-3 border-b border-border flex items-center gap-6 bg-secondary/30">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Current Efficiency</span>
          <span className="text-sm font-mono font-bold text-foreground tabular-nums">{currentEfficiency.toFixed(1)} kg/kWh</span>
        </div>
        <span className="w-px h-4 bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Variance from Baseline</span>
          <span className={`text-sm font-mono font-bold tabular-nums ${variance < 0 ? "text-destructive" : "text-sovereign"}`}>
            {variance > 0 ? "+" : ""}{variance.toFixed(1)}%
          </span>
        </div>
      </div>
      <div className="p-4">
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={enriched} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="gradEnergy" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--sovereign))" stopOpacity={0.25} />
                <stop offset="95%" stopColor="hsl(var(--sovereign))" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradYieldOk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(185,70%,50%)" stopOpacity={0.25} />
                <stop offset="95%" stopColor="hsl(185,70%,50%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradLeakage" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--gap-detected))" stopOpacity={0.45} />
                <stop offset="95%" stopColor="hsl(var(--gap-detected))" stopOpacity={0.08} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" vertical={false} />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 9, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={{ stroke: "hsl(240,4%,16%)" }}
              tickLine={false}
            />
            <YAxis
              yAxisId="energy"
              domain={[0, 'auto']}
              tick={{ fontSize: 10, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={false}
              tickLine={false}
              label={{ value: "kWh", angle: -90, position: "insideLeft", fontSize: 9, fill: "hsl(240,5%,40%)", dx: 10 }}
            />
            <YAxis
              yAxisId="yield"
              orientation="right"
              domain={[0, 'auto']}
              tick={{ fontSize: 10, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={false}
              tickLine={false}
              label={{ value: "kg", angle: 90, position: "insideRight", fontSize: 9, fill: "hsl(240,5%,40%)", dx: -10 }}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(240,5%,7%)",
                border: "1px solid hsl(240,4%,16%)",
                borderRadius: 6,
                fontSize: 11,
                fontFamily: "JetBrains Mono",
                color: "hsl(0,0%,93%)",
              }}
              labelStyle={{ color: "hsl(240,5%,50%)" }}
              formatter={(value: number, name: string) => {
                if (name === "energy") return [`${value.toFixed(1)} kWh`, "Energy"];
                if (name === "yieldHealthy") return [`${value.toFixed(1)} kg`, "Yield"];
                if (name === "yieldLeakage") return [`${value.toFixed(1)} kg`, "⚠ Leakage Zone"];
                return [value, name];
              }}
            />
            <ReferenceLine
              yAxisId="yield"
              y={LEAKAGE_THRESHOLD}
              stroke="hsl(var(--gap-detected))"
              strokeDasharray="4 4"
              strokeOpacity={0.5}
            />
            <Area
              yAxisId="energy"
              type="monotone"
              dataKey="energy"
              stroke="hsl(var(--sovereign))"
              strokeWidth={2}
              fill="url(#gradEnergy)"
              name="energy"
            />
            <Area
              yAxisId="yield"
              type="monotone"
              dataKey="yieldHealthy"
              stroke="hsl(185,70%,50%)"
              strokeWidth={2}
              fill="url(#gradYieldOk)"
              name="yieldHealthy"
            />
            <Area
              yAxisId="yield"
              type="monotone"
              dataKey="yieldLeakage"
              stroke="hsl(var(--gap-detected))"
              strokeWidth={1.5}
              fill="url(#gradLeakage)"
              name="yieldLeakage"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
