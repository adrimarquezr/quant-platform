# Apache Superset — Quant BI Dashboards

Este directorio contiene las vistas SQL y la configuración de datasets analíticos para la visualización cuantitativa en Apache Superset.

## Dashboards Disponibles en Fase 2

### 1. Portfolio Management Dashboard
- **Equity Curve & NAV**: Evolución temporal del valor liquidativo (NAV) y cash disponible (`v_portfolio_equity_curve`).
- **Asset Allocation**: Distribución de pesos por activo, clase de activo y sector (`v_portfolio_holdings`).
- **P&L Breakdown**: Desglose de PnL no realizado y rentabilidades acumuladas.

### 2. Risk Management Dashboard
- **VaR & CVaR (Expected Shortfall)**: Métricas de pérdida potencial al 95% de confianza (`v_risk_metrics_summary`).
- **Drawdown Analysis**: Seguimiento del drawdown actual, drawdown máximo y factores de recuperación.
- **Concentration & Gross Exposure**: Índice Herfindahl-Hirschman (HHI) y apalancamiento bruto.
- **Risk Limit Violations**: Tabla de auditoría en tiempo real con todas las infracciones de límites de riesgo (`v_risk_violations_audit`).

### 3. Strategy Performance Comparison Dashboard
- **Benchmarking Multiestrategia**: Comparativa directa de *Momentum*, *Mean Reversion* y benchmarks (`v_strategy_comparison`).
- **Métricas Clave**: Sharpe Ratio, Sortino Ratio, Calmar Ratio, Win Rate, Profit Factor, Volatilidad anualizada y Max Drawdown.

### 4. Data Quality Audit Dashboard
- **Quality Run History**: Auditoría por activo de validaciones de integridad de precios, gaps y consistencia OHLC (`v_data_quality_audit`).

## Conexión a Base de Datos en Superset

1. Acceder a Superset: `http://localhost:8088` (Credenciales por defecto: `admin` / `admin`).
2. Añadir Database Connection:
   - **Database Name**: `QuantPlatform`
   - **SQLAlchemy URI**: `postgresql://quant_user:change_me_in_production@postgres:5432/quant_platform`
3. Ejecutar las vistas definidas en `infra/superset/queries_and_views.sql`.
