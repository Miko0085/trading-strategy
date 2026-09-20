import { OrderCalculationResult } from "../types";
import { translateValidation } from "../validation";

export function ValidationMessages({ calculated }: { calculated?: OrderCalculationResult }) {
  const errors = calculated?.validation_errors ?? [];
  return errors.length ? <div className="validation-messages">{errors.map((error, index) => <span key={index}>⚠ {translateValidation(error)}</span>)}</div> : null;
}
