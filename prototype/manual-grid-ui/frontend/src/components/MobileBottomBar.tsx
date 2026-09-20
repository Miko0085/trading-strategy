import { Activity, History, Save } from "lucide-react";

export function MobileBottomBar({ statePage, onConstructor, onState, onHistory, onSave, saving }: { statePage: boolean; onConstructor: () => void; onState: () => void; onHistory: () => void; onSave: () => void; saving: boolean }) {
  return <nav className="mobile-bottom-bar" aria-label="Основная навигация"><button className={!statePage ? "active" : ""} onClick={onConstructor}><span>⌂</span>Сетка</button><button className={statePage ? "active" : ""} onClick={onState}><Activity size={18}/>Факты</button><button onClick={onHistory}><History size={18}/>История</button><button className="mobile-save-action" onClick={onSave}><Save size={18}/>{saving ? "Сохранение" : "Сохранить"}</button></nav>;
}
