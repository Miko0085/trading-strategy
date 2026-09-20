import { describe, expect, it } from "vitest";
import { translateValidation } from "./validation";

describe("validation translations", () => {
  it("translates order-level validation strings", () => {
    expect(translateValidation("qty must be >= 0.001")).toBe("Минимальный объём: 0.001");
    expect(translateValidation("qty must respect qty_step 0.001")).toBe("Объём должен быть кратен шагу: 0.001");
    expect(translateValidation("notional must be >= 5")).toBe("Минимальная стоимость ордера: 5");
  });

  it("translates capital and TP errors", () => {
    expect(translateValidation("TP close_pct total must be <= 100")).toContain("превышает 100%");
    expect(translateValidation("full grid exceeds allocation limit")).toContain("выделенный лимит");
  });
});
