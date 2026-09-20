# Модель данных

**Статус: RECORDER РЕАЛИЗОВАН / STRATEGY И EXECUTION MODEL ПРОЕКТИРУЮТСЯ**

## Recorder — фактическая реальность

Recorder хранит orders, executions, positions, closed_pnl, funding, current_states, observations и timeline.

## Strategy Intent

### Grid / GridCycle
Долгоживущая сетка и контекст текущей geometry/anchor.

### GridGeometry
Концептуальные поля: order_count, depth_pct, first_offset_pct, distribution_coefficient, relative_spacing, anchor/reference, geometry revision.

### GridSizingPolicy
mode manual/generated, base size/notional, martingale coefficient, dynamic sizing policy version.

### CapitalAllocationPolicy
long_pct, short_pct, reserve_pct.

### GridSideConfig
enabled_long, enabled_short.

### GridRevision
Immutable snapshot будущей конфигурации.

### GridOrderConfig
side, level, source mode, geometry reference, planned_notional, configured_qty, TP configuration.

### PositionModeSnapshot
Factual state: symbol, HEDGE/ONE_WAY/UNKNOWN, observed_at. Position Mode не является Trader Intent.

### RestructuringTrigger
type, source factual event, timestamp.

### RestructuringPlan
trigger, capital snapshot, allocation snapshot, geometry reference, qty changes, optional anchor change, keep/cancel/amend/create, target revision.

## Execution

ApprovedExecutionPlan → ExecutionCommand → ExchangeOrder → Execution.

## Attribution

StrategyLot/Filled Allocation хранит source GridOrderConfig, executions, configured_qty, filled_qty, actual average fill, open_qty, closed_qty, realized PnL и TP state.

## Главная цепочка

INTENT → RISK DECISION → APPROVED EXECUTION → EXCHANGE REALITY → LOT ATTRIBUTION → RESTRUCTURING TRIGGER → NEW INTENT REVISION.
