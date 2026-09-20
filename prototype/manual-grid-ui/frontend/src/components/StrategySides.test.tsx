/** @vitest-environment jsdom */
import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { initialAccount } from "../domain";
import { StrategySides } from "./StrategySides";

beforeAll(() => { (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; });

function render(mode: "HEDGE" | "ONE_WAY" | "UNKNOWN", enabledLong = true, enabledShort = false) {
  const container = document.createElement("div"); document.body.appendChild(container);
  const root = createRoot(container);
  const onToggle = vi.fn();
  act(() => root.render(<StrategySides account={{ ...initialAccount, symbol: "ETHUSDT", positionMode: mode }} enabledLong={enabledLong} enabledShort={enabledShort} onToggle={onToggle}/>));
  return { container, root, onToggle };
}

describe("StrategySides", () => {
  it("shows factual Hedge Mode and permits either side toggle", () => {
    const view = render("HEDGE");
    expect(view.container.textContent).toContain("Hedge Mode");
    act(() => (view.container.querySelectorAll("button")[1] as HTMLButtonElement).click());
    expect(view.onToggle).toHaveBeenCalledWith("short");
    view.root.unmount(); view.container.remove();
  });

  it("does not disable the second side in One-Way UI", () => {
    const view = render("ONE_WAY");
    const short = view.container.querySelectorAll("button")[1] as HTMLButtonElement;
    expect(short.disabled).toBe(false);
    expect(view.container.textContent).toContain("One-Way");
    view.root.unmount(); view.container.remove();
  });
});
