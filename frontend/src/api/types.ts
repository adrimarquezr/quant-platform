/**
 * TypeScript types matching the FastAPI Pydantic schemas in apps/api/schemas.py.
 *
 * These are the API contract — kept in sync manually with the backend.
 * TODO: Auto-generate via openapi-typescript when CI pipeline supports it.
 */

// =============================================================================
// Health
// =============================================================================

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

// =============================================================================
// Assets
// =============================================================================

export interface AssetResponse {
  id: string;
  symbol: string;
  name: string;
  asset_class: string;
  exchange: string;
  currency: string;
  sector: string | null;
  is_active: boolean;
}

export interface AssetCreate {
  symbol: string;
  name: string;
  asset_class?: string;
  exchange?: string;
  currency?: string;
  sector?: string | null;
}

// =============================================================================
// Market Data
// =============================================================================

export interface MarketDataRequest {
  symbol: string;
  start_date: string;
  end_date: string;
  frequency?: string;
  provider?: string;
}

export interface MarketDataSummary {
  symbol: string;
  provider: string;
  frequency: string;
  start_date: string;
  end_date: string;
  row_count: number;
  parquet_path: string;
}

export interface PriceBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close: number | null;
}

// =============================================================================
// Strategies
// =============================================================================

export interface StrategyInfo {
  name: string;
  version: string;
  category: string;
  parameter_schema: Record<string, ParameterDef>;
}

export interface ParameterDef {
  type: string;
  default: number | string | boolean;
  min?: number;
  max?: number;
  description?: string;
}

export interface StrategySchemaResponse {
  strategy_name: string;
  version: string;
  parameters: Record<string, ParameterDef>;
}

// =============================================================================
// Backtests
// =============================================================================

export interface BacktestRequest {
  strategy_name: string;
  parameters?: Record<string, number | string | boolean>;
  universe?: string[];
  start_date?: string;
  end_date?: string;
  initial_cash?: number;
  commission_rate_bps?: number;
  slippage_rate_bps?: number;
  frequency?: string;
}

export interface BacktestMetrics {
  total_return: number;
  cagr: number;
  annualized_volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_trade_return: number;
  best_trade: number;
  worst_trade: number;
  exposure_time: number;
  turnover: number;
  final_equity: number;
}

export interface BacktestResponse {
  id: string;
  strategy_name: string;
  status: string;
  metrics: BacktestMetrics;
  equity_curve: number[];
  dates: string[];
  execution_time_ms: number;
  config: Record<string, unknown>;
}

export interface BacktestSummary {
  id: string;
  strategy_name: string;
  status: string;
  total_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  execution_time_ms: number | null;
  started_at: string | null;
}

// =============================================================================
// Data Quality
// =============================================================================

export interface DataQualityCheckResponse {
  check_name: string;
  status: string;
  message: string;
  details: Record<string, number | string>;
}

export interface DataQualityReportResponse {
  dataset: string;
  symbol: string;
  status: string;
  is_valid: boolean;
  rows_checked: number;
  errors: string[];
  checks: DataQualityCheckResponse[];
  timestamp: string;
}

export interface DataQualityRunSummary {
  id: string;
  dataset: string;
  symbol: string;
  status: string;
  rows_checked: number;
  created_at: string;
}

// =============================================================================
// Portfolios & Positions
// =============================================================================

export interface PortfolioCreateRequest {
  name: string;
  description?: string;
  initial_cash?: number;
}

export interface PositionResponse {
  symbol: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  weight: number;
}

export interface PortfolioSummary {
  id: string;
  name: string;
  description: string;
  cash: number;
  total_value: number;
  updated_at: string;
}

export interface PortfolioSnapshotResponse {
  timestamp: string;
  total_value: number;
  cash: number;
  positions_value: number;
  daily_return: number | null;
}

export interface PortfolioPerformanceResponse {
  portfolio_id: string;
  total_value: number;
  cash: number;
  snapshots: PortfolioSnapshotResponse[];
}

// =============================================================================
// Risk Management
// =============================================================================

export interface RiskViolationResponse {
  rule_name: string;
  description: string;
  actual_value: number;
  limit_value: number;
  severity: string;
}

export interface RiskMetricResponse {
  timestamp: string;
  var_95: number;
  cvar_95: number;
  volatility: number;
  max_drawdown: number;
  current_drawdown: number;
  gross_exposure: number;
  net_exposure: number;
  concentration_hhi: number;
  beta: number | null;
  verdict: string;
  violations: RiskViolationResponse[];
}

// =============================================================================
// Common / Job Status (prepared for async jobs)
// =============================================================================

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface ApiError {
  detail: string | { message: string; errors: string[] };
}
