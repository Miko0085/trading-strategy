/** @vitest-environment jsdom */
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { initialAccount } from "./domain";
import { StateView } from "./components/StateView";
import { SymbolSelector } from "./components/SymbolSelector";
import { UtilizationGauge } from "./components/UtilizationGauge";

const wait = (milliseconds: number) => new Promise<void>((resolve) => setTimeout(resolve, milliseconds));

function render(element: React.ReactElement): { container: HTMLDivElement; root: Root } {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(element));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

beforeAll(() => { (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; });

describe("Risk Meter DOM", () => {
  it("renders a neutral meter with six empty values before calculation", () => {
    const { container } = render(<UtilizationGauge side="long"/>);
    expect(container.querySelector('[data-testid="risk-meter-long"]')).not.toBeNull();
    expect(container.querySelector(".risk-meter")?.className).toContain("neutral");
    expect(container.querySelector('[data-testid="risk-active-window"]')?.textContent).toBe("—");
    expect(container.querySelector('[data-testid="risk-queue"]')?.textContent).toBe("—");
    expect(container.querySelector('[data-testid="risk-full-grid"]')?.textContent).toBe("—");
  });

  it("renders separate authoritative margin metrics", () => {
    const { container } = render(<UtilizationGauge side="long" calculation={{ side: "long", orders: [], active_window_levels: [1], queued_levels: [2], full_grid_planned_margin: 70, active_window_planned_margin: 20, queued_planned_margin: 50, planned_qty: 1, planned_average: 100, aggregate_tp_gross_pnl: 0, aggregate_fee_estimate: null, aggregate_net_pnl: null, allocation_limit: 100, remaining_limit: 30, utilization_pct: 70, excess: null, validation_errors: [], status: "VALID" }}/>);
    expect(container.querySelector('[data-testid="risk-limit"]')?.textContent).toContain("100");
    expect(container.querySelector('[data-testid="risk-active-window"]')?.textContent).toContain("20");
    expect(container.querySelector('[data-testid="risk-queue"]')?.textContent).toContain("50");
    expect(container.querySelector('[data-testid="risk-full-grid"]')?.textContent).toContain("70");
    expect(container.querySelector('[data-testid="risk-remaining"]')?.textContent).toContain("30");
    expect(container.querySelector('[data-testid="risk-active-window"]')?.textContent).not.toBe(container.querySelector('[data-testid="risk-full-grid"]')?.textContent);
    expect(container.querySelector('[data-testid="risk-arc"]')?.getAttribute("style")).toContain("--risk-progress: 126deg");
  });

  it("keeps the meter visible in danger and shows exact excess", () => {
    const { container } = render(<UtilizationGauge side="short" calculation={{ side: "short", orders: [], active_window_levels: [], queued_levels: [], full_grid_planned_margin: 120, active_window_planned_margin: 120, queued_planned_margin: 0, planned_qty: 1, planned_average: 100, aggregate_tp_gross_pnl: 0, aggregate_fee_estimate: null, aggregate_net_pnl: null, allocation_limit: 100, remaining_limit: -20, utilization_pct: 120, excess: 20, validation_errors: [], status: "BLOCKED" }}/>);
    expect(container.querySelector('[data-testid="risk-meter-short"]')?.className).toContain("danger");
    expect(container.querySelector('[data-testid="risk-excess"]')?.textContent).toContain("20");
    expect(container.textContent).toContain("Точное превышение");
  });
});

describe("StateView DOM", () => {
  it("shows empty and unavailable order states", () => {
    const empty = render(<StateView account={{ ...initialAccount, ordersAvailable: true, openOrders: [] }}/>);
    expect(empty.container.textContent).toContain("Активных ордеров нет");
    empty.root.unmount();
    const unavailable = render(<StateView account={{ ...initialAccount, ordersAvailable: false, openOrders: [], ordersError: "Bybit timeout" }}/>);
    expect(unavailable.container.textContent).toContain("Не удалось получить активные ордера Bybit");
    expect(unavailable.container.textContent).toContain("Bybit timeout");
  });
});

describe("SymbolSelector DOM", () => {
  it("opens, navigates, selects, and closes with keyboard and mouse", async () => {
    const onChange = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ symbols: ["BTCUSDT", "ETHUSDT"] }), { status: 200, headers: { "Content-Type": "application/json" } }))));
    const { container, root } = render(<SymbolSelector value="BTCUSDT" symbols={["BTCUSDT", "ETHUSDT"]} onChange={onChange}/>);
    const input = container.querySelector("input") as HTMLInputElement;
    act(() => { input.blur(); input.focus(); });
    await act(async () => { await wait(300); });
    expect(input.getAttribute("aria-expanded")).toBe("true");
    const buttons = () => Array.from(container.querySelectorAll<HTMLButtonElement>(".symbol-results button"));
    expect(buttons()[0].className).toContain("highlighted");
    act(() => input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true })));
    expect(buttons()[1].className).toContain("highlighted");
    act(() => input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true })));
    expect(buttons()[0].className).toContain("highlighted");
    act(() => root.render(<SymbolSelector value="ETHUSDT" symbols={["BTCUSDT", "ETHUSDT"]} onChange={onChange}/>));
    await act(async () => { await wait(300); });
    expect(buttons()[0].className).toContain("highlighted");
    act(() => input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true })));
    act(() => input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })));
    expect(onChange).toHaveBeenCalledWith("ETHUSDT");
    expect(input.getAttribute("aria-expanded")).toBe("false");
    act(() => { input.blur(); input.focus(); });
    act(() => input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(input.getAttribute("aria-expanded")).toBe("false");
    act(() => { input.blur(); input.focus(); });
    await act(async () => { await wait(300); });
    act(() => buttons()[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true })));
    expect(onChange).toHaveBeenCalledWith("BTCUSDT");
    act(() => document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true })));
    expect(input.getAttribute("aria-expanded")).toBe("false");
  });

  it("shows loading and empty results, and skips remote search for empty query", async () => {
    const pending = new Promise<Response>(() => undefined);
    const fetchMock = vi.fn().mockReturnValue(pending);
    vi.stubGlobal("fetch", fetchMock);
    const loading = render(<SymbolSelector value="BTC" symbols={[]} onChange={vi.fn()}/>);
    const loadingInput = loading.container.querySelector("input") as HTMLInputElement;
    act(() => loadingInput.focus());
    await act(async () => { await wait(300); });
    expect(loading.container.textContent).toContain("Загрузка…");
    loading.root.unmount();

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ symbols: [] }), { status: 200, headers: { "Content-Type": "application/json" } })));
    const empty = render(<SymbolSelector value="DOGE" symbols={[]} onChange={vi.fn()}/>);
    const emptyInput = empty.container.querySelector("input") as HTMLInputElement;
    act(() => emptyInput.focus());
    await act(async () => { await wait(300); });
    expect(empty.container.textContent).toContain("Ничего не найдено");
    empty.root.unmount();

    const noQueryFetch = vi.fn();
    vi.stubGlobal("fetch", noQueryFetch);
    const blank = render(<SymbolSelector value="" symbols={[]} onChange={vi.fn()}/>);
    const blankInput = blank.container.querySelector("input") as HTMLInputElement;
    act(() => blankInput.focus());
    await act(async () => { await wait(300); });
    expect(noQueryFetch).not.toHaveBeenCalled();
  });
});
