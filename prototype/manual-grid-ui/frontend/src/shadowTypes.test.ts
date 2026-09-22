import { describe, expect, it } from "vitest";
import { defaultGeneratedSide, effectiveDistributionCoefficient } from "./shadowTypes";

describe("generated grid distribution mode", () => {
  it("uses the selected K when logarithmic distribution is enabled", () => {
    const config = defaultGeneratedSide(true);
    config.logarithmicDistributionEnabled = true;
    config.distributionCoefficient = 0.8;
    expect(effectiveDistributionCoefficient(config)).toBe(0.8);
  });

  it("forces K=1 for linear distribution while preserving the selected K", () => {
    const config = defaultGeneratedSide(true);
    config.logarithmicDistributionEnabled = false;
    config.distributionCoefficient = 0.8;
    expect(effectiveDistributionCoefficient(config)).toBe(1);
    expect(config.distributionCoefficient).toBe(0.8);
  });
});
