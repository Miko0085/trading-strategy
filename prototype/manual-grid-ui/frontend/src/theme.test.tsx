/** @vitest-environment jsdom */
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "./components/ThemeToggle";

afterEach(() => { document.documentElement.dataset.theme = "dark"; window.localStorage.clear(); document.body.innerHTML = ""; });

describe("theme toggle", () => {
  it("switches theme and persists the choice locally", () => {
    const container = document.createElement("div"); document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<ThemeToggle/>));
    const button = container.querySelector("button") as HTMLButtonElement;
    act(() => button.click());
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("manual-grid-theme")).toBe("light");
    expect(button.getAttribute("aria-label")).toContain("тёмную");
    root.unmount();
  });
});
