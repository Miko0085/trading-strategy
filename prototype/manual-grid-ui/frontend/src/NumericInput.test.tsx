/** @vitest-environment jsdom */
import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { NumericInput } from "./components/NumericInput";

beforeAll(() => { (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; });

describe("NumericInput", () => {
  it("keeps the field blank while replacing a value", () => {
    const onValueChange = vi.fn();
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<NumericInput value={12} type="number" commitEmpty={false} onValueChange={onValueChange} />));
    const input = container.querySelector("input") as HTMLInputElement;
    act(() => { input.focus(); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, ""); input.dispatchEvent(new Event("input", { bubbles: true })); });
    expect(input.value).toBe("");
    expect(onValueChange).not.toHaveBeenCalled();
    act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, "34"); input.dispatchEvent(new Event("input", { bubbles: true })); });
    expect(input.value).toBe("34");
    expect(onValueChange).toHaveBeenCalledWith(34);
    root.unmount();
  });
});
