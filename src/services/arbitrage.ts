export type ArbitrageStatus = {
  symbol: string;
  trade_size: number;
  balance_usd: number;
  total_pnl_usd: number;
  active_exchanges: string[];
  latest_opportunity: ArbitrageOpportunity | null;
};

export type ArbitrageOpportunity = {
  timestamp: string;
  status: "accepted" | "discarded";
  reason: string;
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  trade_size: number;
  gross_spread_pct: number;
  net_spread_pct: number;
  expected_profit_usd: number;
  latency_ms: number;
  buy_vwap: number;
  sell_vwap: number;
};

export type SimulatedTrade = {
  timestamp: string;
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  size: number;
  pnl_usd: number;
  latency_ms: number;
};

export type SpreadPoint = {
  timestamp: string;
  spread_gross_pct: number;
  spread_net_pct: number;
  expected_profit_usd: number;
  status: "accepted" | "discarded";
  reason: string;
  pair: string;
  trigger_exchange: string;
  latency_ms: number;
};

const ENV_API_BASE = (
  (import.meta.env as any).VITE_API_BASE_URL as string | undefined
)?.replace(/\/$/, "");

const API_BASE_CANDIDATES = ENV_API_BASE
  ? [ENV_API_BASE]
  : [
      "http://127.0.0.1:8000",
      "http://localhost:8000",
      "http://127.0.0.1:8001",
      "http://localhost:8001",
    ];

let resolvedApiBase: string | null = ENV_API_BASE ?? null;

function orderedBases(): string[] {
  if (!resolvedApiBase) return API_BASE_CANDIDATES;
  return [
    resolvedApiBase,
    ...API_BASE_CANDIDATES.filter((base) => base !== resolvedApiBase),
  ];
}

async function requestJson<T>(path: string): Promise<T> {
  let lastError = "Backend indisponível";

  for (const base of orderedBases()) {
    try {
      const response = await fetch(`${base}${path}`);
      if (!response.ok) {
        lastError = `API error ${response.status} em ${base}`;
        continue;
      }

      resolvedApiBase = base;
      return (await response.json()) as T;
    } catch {
      lastError = `Sem ligação a ${base}`;
    }
  }

  throw new Error(lastError);
}

export async function getArbitrageStatus(): Promise<ArbitrageStatus> {
  return requestJson<ArbitrageStatus>("/api/arbitrage/status");
}

export async function getArbitrageOpportunities(
  limit = 100,
): Promise<ArbitrageOpportunity[]> {
  const data = await requestJson<{ items: ArbitrageOpportunity[] }>(
    `/api/arbitrage/opportunities?limit=${limit}`,
  );
  return data.items;
}

export async function getArbitrageTrades(
  limit = 50,
): Promise<SimulatedTrade[]> {
  const data = await requestJson<{ items: SimulatedTrade[] }>(
    `/api/arbitrage/trades?limit=${limit}`,
  );
  return data.items;
}

export async function getSpreadSeries(limit = 50): Promise<SpreadPoint[]> {
  const data = await requestJson<{ items: SpreadPoint[] }>(
    `/api/arbitrage/spread-series?limit=${limit}`,
  );
  return data.items;
}

export function connectArbitrageSocket(
  onSnapshot: (payload: {
    snapshot: ArbitrageStatus;
    spread_series: SpreadPoint[];
  }) => void,
): WebSocket {
  const base =
    resolvedApiBase ?? API_BASE_CANDIDATES[0] ?? "http://127.0.0.1:8000";
  const wsBase = base.replace(/^http/, "ws");
  const socket = new WebSocket(`${wsBase}/ws/arbitrage`);

  socket.addEventListener("message", (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "arbitrage_snapshot") {
        onSnapshot({
          snapshot: message.snapshot as ArbitrageStatus,
          spread_series: (message.spread_series ?? []) as SpreadPoint[],
        });
      }
    } catch {
      // ignore malformed ws payload
    }
  });

  return socket;
}
