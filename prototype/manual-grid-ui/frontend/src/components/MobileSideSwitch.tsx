import { Side } from "../domain";

export function MobileSideSwitch({ selected, onChange }: { selected: Side; onChange: (side: Side) => void }) {
  return <div className="mobile-side-switch" role="tablist" aria-label="Сторона сетки"><button role="tab" aria-selected={selected === "long"} className={selected === "long" ? "active" : ""} onClick={() => onChange("long")}>ЛОНГ</button><button role="tab" aria-selected={selected === "short"} className={selected === "short" ? "active" : ""} onClick={() => onChange("short")}>ШОРТ</button></div>;
}
