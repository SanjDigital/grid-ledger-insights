export interface Mill {
  id: string;
  name: string;
  operator: string;
  meterId: string;
  phone: string;
  assetClass: string;
}

export interface StreakDay {
  day: number;
  status: "sovereign" | "review" | "gap" | "pending";
}

export type AnomalyType = "holiday-heist" | "leading-day" | "m1-corridor";

export interface AnomalyFlag {
  type: AnomalyType;
  label: string;
  detail: string;
}

export interface VerifiedEvent {
  id: string;
  timestamp: string;
  tokenId: string;
  kwh: number;
  reportedCash: number;
  currency: string;
  verification: "sovereign" | "review" | "gap" | "floor-verified";
  anomalies?: AnomalyFlag[];
  tokenPurchaseTimestamp?: string;
  airtelTimestamp?: string;
  isPeakHour?: boolean;
  revenueUplift?: number;
  yieldKg: number; // actual grain output measured by scale
  meteredKwh: number; // external meter reading (Layer 4 authority)
  gridOutage?: boolean; // ESCOM-confirmed grid interruption (Q2 2026 Amendment 1)
}

export type SystemState = "VERIFIED" | "UNDER REVIEW" | "COMPROMISED" | "SUSPENDED";
export type TrustTier = "INSTITUTIONAL" | "COMMERCIAL" | "SUBPRIME" | "HIGH RISK";

export interface ForensicData {
  rootHash: string;
  signatureAlgo: string;
  signatureStatus: "Valid" | "Invalid";
  physicsVariance: number;
  trustScore: number;
  bpsAdjustment: number;
  leverageCap: number;
  institutionalGrade: string;
  // v2.4.1 additions
  secRange: [number, number]; // kWh/kg calibration bounds
  currentSEC: number;
  ear: number; // Energy Accountability Ratio (%)
  earGap: number; // % gap
  systemState: SystemState;
  trustTier: TrustTier;
  ntpOffset: number; // seconds offset from NTP
  lastCalibration: string;
}

export const mills: Mill[] = [
  { id: "mill-1", name: "Jeremiah", operator: "Nabiwi Chitsazo", meterId: "37154463253", phone: "0998-265-527", assetClass: "3-Phase Maize Mill (M1 Artery)" },
  { id: "mill-2", name: "Solomon", operator: "Chimwemwe Banda", meterId: "37154463287", phone: "0991-442-108", assetClass: "3-Phase Maize Mill (M1 Artery)" },
  { id: "mill-3", name: "Ezekiel", operator: "Tadala Phiri", meterId: "37154463301", phone: "0885-771-934", assetClass: "3-Phase Maize Mill (M1 Artery)" },
  { id: "mill-4", name: "Nehemiah", operator: "Kondwani Mwale", meterId: "37154463319", phone: "0997-338-662", assetClass: "3-Phase Maize Mill (M1 Artery)" },
  { id: "mill-5", name: "Isaiah", operator: "Mphatso Chirwa", meterId: "37154463342", phone: "0884-559-213", assetClass: "3-Phase Maize Mill (M1 Artery)" },
];

export const generateStreakDays = (): StreakDay[] =>
  Array.from({ length: 30 }, (_, i) => ({
    day: i + 1,
    status: i < 27 ? "sovereign" : i === 27 ? "review" : i === 28 ? "sovereign" : "pending",
  }));

export const forensicData: ForensicData = {
  rootHash: "a7f3c9e2d1b8...4f6a",
  signatureAlgo: "Ed25519",
  signatureStatus: "Valid",
  physicsVariance: 1.2,
  trustScore: 84,
  bpsAdjustment: -500,
  leverageCap: 3.5,
  institutionalGrade: "Commercial",
  // v2.4.1
  secRange: [0.038, 0.042],
  currentSEC: 0.0395,
  ear: 92.3,
  earGap: 7.7,
  systemState: "UNDER REVIEW",
  trustTier: "COMMERCIAL",
  ntpOffset: 2.3,
  lastCalibration: "2026-03-28",
};

export const verifiedEvents: VerifiedEvent[] = [
  { id: "evt-001", timestamp: "2024-03-15 14:32:07", airtelTimestamp: "2024-03-15 15:32:07", tokenId: "TKN-9A3F2", kwh: 59.9, reportedCash: 80865, currency: "K", verification: "sovereign", isPeakHour: true, revenueUplift: 16.2, yieldKg: 1510, meteredKwh: 64.2 },
  { id: "evt-002", timestamp: "2024-03-15 13:18:42", airtelTimestamp: "2024-03-15 14:18:42", tokenId: "TKN-8B2E1", kwh: 61.2, reportedCash: 82621, currency: "K", verification: "floor-verified", isPeakHour: true, revenueUplift: 14.8, yieldKg: 1540, meteredKwh: 66.1 },
  { id: "evt-003", timestamp: "2024-03-15 12:05:19", airtelTimestamp: "2024-03-15 13:05:19", tokenId: "TKN-7C1D0", kwh: 58.4, reportedCash: 78840, currency: "K", verification: "sovereign", isPeakHour: true, revenueUplift: 3.1, yieldKg: 1480, meteredKwh: 63.0, anomalies: [{ type: "m1-corridor", label: "M1 CORRIDOR", detail: "Revenue uplift 3.1% vs expected 15% — deviation flagged" }] },
  { id: "evt-004", timestamp: "2024-03-15 10:47:33", airtelTimestamp: "2024-03-15 11:47:33", tokenId: "TKN-6D0C9", kwh: 63.7, reportedCash: 85995, currency: "K", verification: "review", isPeakHour: true, revenueUplift: 15.4, yieldKg: 1420, meteredKwh: 68.9, tokenPurchaseTimestamp: "2024-03-14 16:20:00", anomalies: [{ type: "leading-day", label: "LEADING DAY", detail: "Token purchased Day T, first report Day T+1 — reporting delay detected" }] },
  { id: "evt-005", timestamp: "2024-03-15 09:22:51", airtelTimestamp: "2024-03-15 10:22:51", tokenId: "TKN-5E9B8", kwh: 57.1, reportedCash: 77085, currency: "K", verification: "floor-verified", isPeakHour: true, revenueUplift: 15.1, yieldKg: 1460, meteredKwh: 61.5 },
  { id: "evt-006", timestamp: "2024-03-15 08:11:06", airtelTimestamp: "2024-03-15 09:11:06", tokenId: "TKN-4F8A7", kwh: 60.5, reportedCash: 81675, currency: "K", verification: "sovereign", isPeakHour: true, revenueUplift: 14.9, yieldKg: 1525, meteredKwh: 65.3 },
  { id: "evt-007", timestamp: "2024-01-02 23:55:44", airtelTimestamp: "2024-01-03 00:55:44", tokenId: "TKN-3G7Z6", kwh: 55.8, reportedCash: 75330, currency: "K", verification: "gap", isPeakHour: false, yieldKg: 0, meteredKwh: 60.2, anomalies: [{ type: "holiday-heist", label: "HOLIDAY HEIST", detail: "Energy consumed on public holiday (Jan 2) with no production event" }] },
  { id: "evt-008", timestamp: "2024-03-14 22:40:12", airtelTimestamp: "2024-03-14 23:40:12", tokenId: "TKN-2H6Y5", kwh: 62.3, reportedCash: 84105, currency: "K", verification: "sovereign", isPeakHour: false, revenueUplift: 2.1, yieldKg: 1570, meteredKwh: 67.4 },
  { id: "evt-009", timestamp: "2024-03-15 16:05:00", tokenId: "TKN-1J5X4", kwh: 0, reportedCash: 0, currency: "K", verification: "gap", isPeakHour: true, yieldKg: 0, meteredKwh: 0, gridOutage: true },
];

export const energyVsCashData = [
  { hour: "00:00", kwh: 42.1, cash: 56835 },
  { hour: "02:00", kwh: 38.5, cash: 51975 },
  { hour: "04:00", kwh: 35.2, cash: 47520 },
  { hour: "06:00", kwh: 48.7, cash: 65745 },
  { hour: "08:00", kwh: 57.1, cash: 77085 },
  { hour: "10:00", kwh: 63.7, cash: 85995 },
  { hour: "12:00", kwh: 58.4, cash: 78840 },
  { hour: "14:00", kwh: 59.9, cash: 80865 },
  { hour: "16:00", kwh: 55.3, cash: 74655 },
  { hour: "18:00", kwh: 51.8, cash: 69930 },
  { hour: "20:00", kwh: 46.2, cash: 62370 },
  { hour: "22:00", kwh: 43.9, cash: 59265 },
];

export function getTrustTierColor(tier: TrustTier): string {
  switch (tier) {
    case "INSTITUTIONAL": return "text-[hsl(var(--sovereign))]";
    case "COMMERCIAL": return "text-[hsl(var(--under-review))]";
    case "SUBPRIME": return "text-[hsl(var(--gap-detected))]";
    case "HIGH RISK": return "text-destructive";
  }
}

export function getSystemStateColor(state: SystemState): string {
  switch (state) {
    case "VERIFIED": return "text-[hsl(var(--sovereign))]";
    case "UNDER REVIEW": return "text-[hsl(var(--under-review))]";
    case "COMPROMISED": return "text-[hsl(var(--gap-detected))]";
    case "SUSPENDED": return "text-destructive";
  }
}
