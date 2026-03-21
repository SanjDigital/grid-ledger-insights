import { type VerifiedEvent } from "@/lib/mock-data";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface LiveDataFeedProps {
  events: VerifiedEvent[];
}

export function LiveDataFeed({ events }: LiveDataFeedProps) {
  return (
    <div className="card-terminal animate-slide-up">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Verified Events</h3>
          <p className="text-[10px] font-mono text-muted-foreground mt-0.5">Live transaction feed</p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-glow" />
          <span className="text-[10px] font-mono text-muted-foreground">LIVE</span>
        </div>
      </div>

      <div className="overflow-auto max-h-72 scrollbar-terminal">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              {["Timestamp", "Token ID", "kWh", "Reported Cash", "Verification"].map(h => (
                <TableHead key={h} className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase h-8">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.map((evt) => (
              <TableRow key={evt.id} className="border-border hover:bg-secondary/30 transition-colors duration-150">
                <TableCell className="font-mono text-xs tabular text-muted-foreground py-2.5">{evt.timestamp}</TableCell>
                <TableCell className="font-mono text-xs text-foreground py-2.5">{evt.tokenId}</TableCell>
                <TableCell className="font-mono text-xs tabular text-foreground py-2.5">{evt.kwh.toFixed(1)}</TableCell>
                <TableCell className="font-mono text-xs tabular text-foreground py-2.5">
                  {evt.currency}{evt.reportedCash.toLocaleString()}
                </TableCell>
                <TableCell className="py-2.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                    evt.verification === "sovereign" ? "badge-sovereign" :
                    evt.verification === "floor-verified" ? "badge-floor-verified" :
                    evt.verification === "review" ? "badge-review" :
                    "badge-gap"
                  }`}>
                    {evt.verification === "sovereign" ? "SOVEREIGN" :
                     evt.verification === "floor-verified" ? "FLOOR GEN." :
                     evt.verification === "review" ? "REVIEW" : "GAP"}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
