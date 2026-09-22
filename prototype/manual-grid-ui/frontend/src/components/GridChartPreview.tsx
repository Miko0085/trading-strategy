import { useEffect, useMemo, useRef, useState } from "react";
import { CandlestickSeries, ColorType, createChart, LineStyle, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { X } from "lucide-react";
import { fetchJson } from "../api";
import { AccountState, GridOrder, Side, prices } from "../domain";
import { ShadowProposal } from "../shadowTypes";

type KlineResponse = {
  symbol: string;
  interval: string;
  source: "BYBIT_PUBLIC";
  candles: Array<{ time: number; open: number; high: number; low: number; close: number; volume?: number | null }>;
};

type OverlayOrder = { level: number; price: number; qty: number | null };

function workingOrders(side: Side, orders: GridOrder[], account: AccountState): OverlayOrder[] {
  const calculated = prices(account.markPrice, side, orders, account.instrument?.tickSize ?? null);
  return orders.flatMap((order, index) => {
    const value = order.calculatedEntryPrice ?? calculated[index];
    return value == null ? [] : [{ level: order.level, price: value, qty: order.qty }];
  });
}

function proposalOrders(side: Side, proposal: ShadowProposal | null): OverlayOrder[] {
  const rows = proposal?.sides?.[side]?.orders ?? [];
  return rows.flatMap((order) => {
    const value = Number(order.entry_price);
    return Number.isFinite(value) ? [{ level: order.level, price: value, qty: Number(order.qty) }] : [];
  });
}

function distancePct(previous: number, current: number): number {
  return previous > 0 ? Math.abs(current - previous) / previous * 100 : 0;
}

function ChartCanvas({ symbol, side, orders, markPrice, interval }: { symbol: string; side: Side; orders: OverlayOrder[]; markPrice: number | null; interval: string }) {
  const holder = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [candles, setCandles] = useState<KlineResponse["candles"]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setError("");
    void fetchJson<KlineResponse>(`/api/market/klines/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}&limit=240`)
      .then((result) => { if (!cancelled) setCandles(result.candles); })
      .catch(() => { if (!cancelled) { setCandles([]); setError("Свечи Bybit временно недоступны"); } });
    return () => { cancelled = true; };
  }, [symbol, interval]);

  useEffect(() => {
    if (!holder.current) return;
    const chart = createChart(holder.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#81909f" },
      grid: { vertLines: { color: "rgba(129,144,159,.10)" }, horzLines: { color: "rgba(129,144,159,.10)" } },
      rightPriceScale: { borderColor: "rgba(129,144,159,.25)" },
      timeScale: { borderColor: "rgba(129,144,159,.25)", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 0 },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#36c98f",
      downColor: "#e76f82",
      wickUpColor: "#36c98f",
      wickDownColor: "#e76f82",
      borderVisible: false,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const observer = new ResizeObserver(() => chart.timeScale().fitContent());
    observer.observe(holder.current);
    return () => { observer.disconnect(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart) return;
    series.setData(candles.map((candle) => ({ time: candle.time as UTCTimestamp, open: candle.open, high: candle.high, low: candle.low, close: candle.close })));
    for (const line of series.priceLines()) series.removePriceLine(line);

    if (markPrice != null) {
      series.createPriceLine({ price: markPrice, color: "#f2c86b", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "MARK" });
    }

    let previous = markPrice;
    for (const order of orders) {
      const gap = previous == null ? null : distancePct(previous, order.price);
      const prefix = side === "long" ? "L" : "S";
      const qtyLabel = order.qty == null || !Number.isFinite(order.qty) ? "" : ` · ${order.qty}`;
      const gapLabel = gap == null ? "" : ` · Δ ${gap.toFixed(2)}%`;
      series.createPriceLine({
        price: order.price,
        color: side === "long" ? "#36c98f" : "#e76f82",
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: `${prefix}${order.level}${gapLabel}${qtyLabel}`,
      });
      previous = order.price;
    }
    chart.timeScale().fitContent();
  }, [candles, markPrice, orders, side]);

  return <div className="grid-chart-canvas-wrap">
    <div ref={holder} className="grid-chart-canvas"/>
    {error && <div className="grid-chart-error">{error}</div>}
    {!error && candles.length === 0 && <div className="grid-chart-loading">Загрузка свечей Bybit…</div>}
  </div>;
}

export function GridChartPreview({ account, long, short, generatedPreview }: { account: AccountState; long: GridOrder[]; short: GridOrder[]; generatedPreview: ShadowProposal | null }) {
  const [side, setSide] = useState<Side>("long");
  const [open, setOpen] = useState(false);
  const [interval, setInterval] = useState("15");

  const selectedOrders = useMemo(() => {
    const generated = proposalOrders(side, generatedPreview);
    return generated.length > 0 ? generated : workingOrders(side, side === "long" ? long : short, account);
  }, [account, generatedPreview, long, short, side]);

  const sourceLabel = proposalOrders(side, generatedPreview).length > 0 ? "Generated preview" : "Рабочая сетка";

  const controls = <div className="grid-chart-controls">
    <div className="grid-chart-tabs">
      <button type="button" className={side === "long" ? "selected" : ""} onClick={() => setSide("long")}>LONG</button>
      <button type="button" className={side === "short" ? "selected" : ""} onClick={() => setSide("short")}>SHORT</button>
    </div>
    <label className="grid-chart-interval"><span>TF</span><select value={interval} onChange={(event) => setInterval(event.target.value)}><option value="5">5m</option><option value="15">15m</option><option value="30">30m</option><option value="60">1h</option><option value="240">4h</option><option value="D">1D</option></select></label>
  </div>;

  const body = <><div className="grid-chart-meta"><span>{account.symbol} · {sourceLabel}</span><span>{selectedOrders.length} уровней · расстояния Δ от предыдущего уровня</span></div>{controls}<ChartCanvas symbol={account.symbol} side={side} orders={selectedOrders} markPrice={account.markPrice} interval={interval}/><div className="grid-chart-attribution">Charts by TradingView Lightweight Charts™ · market data: Bybit public API</div></>;

  return <section className="grid-chart-preview">
    <div className="grid-chart-preview-head">
      <div><span className="overline">ВИЗУАЛЬНЫЙ PREVIEW</span><h2>Сетка на реальном графике</h2><small>Свечи Bybit + плановые уровни сетки</small></div>
      <button type="button" className="outline grid-chart-open" onClick={() => setOpen(true)}>Открыть график</button>
    </div>

    <div className="grid-chart-mobile-inline">{body}</div>

    {open && <div className="grid-chart-modal-backdrop" role="dialog" aria-modal="true" aria-label="Preview сетки">
      <div className="grid-chart-modal">
        <div className="grid-chart-modal-head"><div><b>Grid Preview · {account.symbol}</b><small>{sourceLabel}</small></div><button type="button" aria-label="Закрыть preview" onClick={() => setOpen(false)}><X size={18}/></button></div>
        {body}
      </div>
    </div>}
  </section>;
}
