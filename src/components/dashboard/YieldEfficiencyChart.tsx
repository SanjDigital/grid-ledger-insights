import { useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

const generateYieldData = () => {
  const data = [];
  for (let day = 1; day <= 30; day++) {
    const energy = 59.9;
    // Yield starts strong then drops after day 20 to show leakage
    let yield_kg: number;
    if (day <= 18) {
      yield_kg = 48 + Math.random() * 4; // ~48-52 kg, healthy
    } else if (day <= 22) {
      yield_kg = 44 - (day - 18) * 2.5 + Math.random() * 2; // declining
    } else {
      yield_kg = 28 + Math.random() * 5; // low plateau ~28-33 kg
    }
    yield_kg = Math.round(yield_kg * 10) / 10;
    data.push({ day: `D${day}`, energy, yield_kg });
  }
  return data;
};

const LEAKAGE_THRESHOLD = 40;

export function YieldEfficiencyChart() {
  const data = useMemo(() => generateYieldData(), []);

  const enriched = useMemo(
    () =>
      data.map((d) => ({
        ...d,
        yieldHealthy: d.yield_kg >= LEAKAGE_THRESHOLD ? d.yield_kg : LEAKAGE_THRESHOLD,
        yieldLeakage: d.yield_kg < LEAKAGE_THRESHOLD ? d.yield_kg : LEAKAGE_THRESHOLD,
      })),
    [data],
  );

  return (
    <div className="card-terminal animate-slide-up">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Yield Efficiency</h3>
          <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
            30-day energy vs. actual yield — correlation gap analysis
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
          <span className="text-sm font-mono font-bold text-foreground tabular-nums">12.1 kg/kWh</span>
        </div>
        <span className="w-px h-4 bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Variance from Baseline</span>
          <span className="text-sm font-mono font-bold text-[hsl(var(--gap-detected))] tabular-nums">-0.4%</span>
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
              interval={4}
            />
            <YAxis
              yAxisId="energy"
              domain={[0, 80]}
              tick={{ fontSize: 10, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={false}
              tickLine={false}
              label={{ value: "kWh", angle: -90, position: "insideLeft", fontSize: 9, fill: "hsl(240,5%,40%)", dx: 10 }}
            />
            <YAxis
              yAxisId="yield"
              orientation="right"
              domain={[0, 70]}
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
                if (name === "energy") return [`${value} kWh`, "Energy"];
                if (name === "yieldHealthy") return [`${value} kg`, "Yield"];
                if (name === "yieldLeakage") return [`${value} kg`, "⚠ Leakage Zone"];
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
            {/* Energy flat line */}
            <Area
              yAxisId="energy"
              type="monotone"
              dataKey="energy"
              stroke="hsl(var(--sovereign))"
              strokeWidth={2}
              fill="url(#gradEnergy)"
              name="energy"
            />
            {/* Yield healthy portion */}
            <Area
              yAxisId="yield"
              type="monotone"
              dataKey="yieldHealthy"
              stroke="hsl(185,70%,50%)"
              strokeWidth={2}
              fill="url(#gradYieldOk)"
              name="yieldHealthy"
            />
            {/* Yield leakage portion */}
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
