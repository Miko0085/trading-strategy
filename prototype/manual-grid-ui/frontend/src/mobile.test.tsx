/** @vitest-environment jsdom */
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { initialAccount, newOrder } from "./domain";
import { CenterPanel } from "./components/CenterPanel";
import { GridOrderCard } from "./components/GridOrderCard";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { MobileAccountSnapshot } from "./components/MobileAccountSnapshot";
import { MobileBottomBar } from "./components/MobileBottomBar";
import { MobileSideSwitch } from "./components/MobileSideSwitch";
import { TakeProfitEditor } from "./components/TakeProfitEditor";
import { HistoryItem } from "./types";

beforeAll(() => { (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; });
afterEach(() => { document.body.innerHTML = ""; vi.unstubAllGlobals(); });

function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(element));
  return { container, root };
}

describe("mobile presentation components", () => {
  it("switches Long/Short without changing the selected value", () => {
    const change = vi.fn();
    const { container } = mount(<MobileSideSwitch selected="long" onChange={change}/>);
    const buttons = container.querySelectorAll("button");
    expect(buttons[0].getAttribute("aria-selected")).toBe("true");
    act(() => (buttons[1] as HTMLButtonElement).click());
    expect(change).toHaveBeenCalledWith("short");
  });

  it("has compact account details and sticky action controls", () => {
    const snapshot = mount(<MobileAccountSnapshot account={{ ...initialAccount, availableMargin: 81.28, equity: 116.73, walletBalance: 107.97 }}/>);
    expect(snapshot.container.textContent).toContain("Доступная маржа");
    act(() => (snapshot.container.querySelector("button") as HTMLButtonElement).click());
    expect(snapshot.container.textContent).toContain("Initial Margin");
    const actions = mount(<MobileBottomBar statePage={false} onConstructor={vi.fn()} onState={vi.fn()} onHistory={vi.fn()} onSave={vi.fn()} saving={false}/>);
    expect(actions.container.querySelector(".mobile-bottom-bar")).not.toBeNull();
    expect(actions.container.textContent).toContain("Сохранить");
  });

  it("uses a compact collapsed order card on mobile and renders TP mini-cards", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true, addListener: vi.fn(), removeListener: vi.fn() }));
    const order = newOrder("long", 2);
    order.qty = 1;
    order.tps = [{ movePct: 2, closePct: 25 }];
    const card = mount(<GridOrderCard order={order} price={100} tickSize={0.1} leverage={2} active={false} onEdit={vi.fn()} onRemove={vi.fn()}/>);
    expect(card.container.querySelector(".mobile-order-details")).toBeNull();
    act(() => (card.container.querySelector(".collapse") as HTMLButtonElement).click());
    expect(card.container.querySelector(".mobile-order-details")).not.toBeNull();
    expect(card.container.querySelector(".tp-line")).not.toBeNull();
  });

  it("keeps general calculation collapsed until opened and renders history content", () => {
    const center = mount(<CenterPanel account={{ ...initialAccount, markPrice: 100 }} long={[]} short={[]} tickSize={0.1} blocked calculation={null}/>);
    const toggle = center.container.querySelector(".center-mobile-toggle") as HTMLButtonElement;
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    act(() => toggle.click());
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    const item: HistoryItem = { time: "2026-01-01", action: "revision_saved", entityType: "grid_revision", comment: "mobile test" };
    const history = mount(<HistoryDrawer items={[item]} close={vi.fn()}/>);
    expect(history.container.querySelector(".drawer")).not.toBeNull();
    expect(history.container.textContent).toContain("mobile test");
  });

  it("renders TP as a mobile-sized row without dropping values", () => {
    const order = newOrder("long", 1);
    order.tps = [{ movePct: 5, closePct: 25 }];
    const rendered = mount(<TakeProfitEditor order={order} entryPrice={100} tickSize={0.1} backendTps={[]} onChange={vi.fn()}/>);
    expect(rendered.container.querySelector(".tp-line")?.textContent).toContain("Preview");
    expect(rendered.container.querySelector(".tp-line")?.textContent).toContain("Комиссия не задана");
  });
});
