import { energyVsCashData } from "@/lib/mock-data";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function EnergyChart() {
  return (
    <div className="card-terminal animate-slide-up">
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground">Energy vs. Cash Correlation</h3>
        <p className="text-[10px] font-mono text-muted-foreground mt-0.5">24-hour production overlay</p>
      </div>
      <div className="p-4">
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={energyVsCashData} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="gradKwh" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(160,84%,39%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(160,84%,39%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradCash" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(185,70%,50%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(185,70%,50%)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" vertical={false} />
            <XAxis
              dataKey="hour"
              tick={{ fontSize: 10, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={{ stroke: "hsl(240,4%,16%)" }}
              tickLine={false}
            />
            <YAxis
              yAxisId="kwh"
              tick={{ fontSize: 10, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="cash"
              orientation="right"
              tick={{ fontSize: 10, fill: "hsl(240,5%,50%)", fontFamily: "JetBrains Mono" }}
              axisLine={false}
              tickLine={false}
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
            />
            <Area
              yAxisId="kwh"
              type="monotone"
              dataKey="kwh"
              stroke="hsl(160,84%,39%)"
              strokeWidth={2}
              fill="url(#gradKwh)"
              name="kWh"
            />
            <Area
              yAxisId="cash"
              type="monotone"
              dataKey="cash"
              stroke="hsl(185,70%,50%)"
              strokeWidth={2}
              fill="url(#gradCash)"
              name="Cash (K)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
