export type ArbitrageStatus = {
  symbol: string;
  symbols?: string[];
  trade_size: number;
  simulation_volume_usd?: number | null;
  balance_usd: number;
  total_pnl_usd: number;
  portfolio_total_usd?: number;
  active_exchanges: string[];
  inventory_by_exchange?: Record<
    string,
    {
      quote_asset: string;
      quote_balance: number;
      base_asset: string;
      base_balance: number;
      asset_balances?: Record<string, number>;
      total_value_usd?: number;
      status?: string;
    }
  >;
  latest_opportunity: ArbitrageOpportunity | null;
};

export type ArbitrageOpportunity = {
  timestamp: string;
  status: "accepted" | "discarded" | "no_funds" | "insufficient_liquidity";
  reason: string;
  symbol: string;
  symbol_name?: string;
  buy_exchange: string;
  sell_exchange: string;
  trade_size: number;
  gross_spread_pct: number;
  net_spread_pct: number;
  expected_profit_usd: number;
  latency_ms: number;
  buy_vwap: number;
  sell_vwap: number;
  network_fee_asset?: string;
  network_fee_units?: number;
  network_cost_usd?: number;
  buy_book_updated_at: string | null;
  sell_book_updated_at: string | null;
};

export type SimulatedTrade = {
  timestamp: string;
  symbol: string;
  symbol_name?: string;
  buy_exchange: string;
  sell_exchange: string;
  size: number;
  pnl_usd: number;
  latency_ms: number;
  buy_execution_ms?: number;
  sell_execution_ms?: number;
  sync_delay_ms?: number;
};

export type SpreadPoint = {
  timestamp: string;
  spread_gross_pct: number;
  spread_net_pct: number;
  expected_profit_usd: number;
  status: "accepted" | "discarded" | "no_funds" | "insufficient_liquidity";
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

async function requestJsonPost<T>(path: string, body: unknown): Promise<T> {
  let lastError = "Backend indisponível";

  for (const base of orderedBases()) {
    try {
      const response = await fetch(`${base}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
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

export async function setSimulationVolumeUsd(
  simulationVolumeUsd: number | null,
): Promise<ArbitrageStatus> {
  return requestJsonPost<ArbitrageStatus>("/api/arbitrage/simulation-volume", {
    simulation_volume_usd: simulationVolumeUsd,
  });
}

export async function rebalanceArbitrageWallets(): Promise<{
  snapshot: ArbitrageStatus;
  rebalance: {
    transfers: number;
    moved_quote_usd: number;
    target_quote_usd: number;
  };
}> {
  return requestJsonPost<{
    snapshot: ArbitrageStatus;
    rebalance: {
      transfers: number;
      moved_quote_usd: number;
      target_quote_usd: number;
    };
  }>("/api/arbitrage/rebalance", {});
}

export async function getArbitrageOpportunities(
  limit = 100,
  symbols: string[] = [],
  simulationVolumeUsd?: number,
): Promise<ArbitrageOpportunity[]> {
  const querySymbols = symbols
    .map((s) => `symbols=${encodeURIComponent(s)}`)
    .join("&");
  const queryVolume =
    simulationVolumeUsd && simulationVolumeUsd > 0
      ? `simulation_volume_usd=${encodeURIComponent(simulationVolumeUsd)}`
      : "";
  const query = [`limit=${limit}`, querySymbols, queryVolume]
    .filter(Boolean)
    .join("&");
  const data = await requestJson<{ items: ArbitrageOpportunity[] }>(
    `/api/arbitrage/opportunities?${query}`,
  );
  return data.items;
}

export async function getArbitrageTrades(
  limit = 50,
  symbols: string[] = [],
): Promise<SimulatedTrade[]> {
  const querySymbols = symbols
    .map((s) => `symbols=${encodeURIComponent(s)}`)
    .join("&");
  const query = [`limit=${limit}`, querySymbols].filter(Boolean).join("&");
  const data = await requestJson<{ items: SimulatedTrade[] }>(
    `/api/arbitrage/trades?${query}`,
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
