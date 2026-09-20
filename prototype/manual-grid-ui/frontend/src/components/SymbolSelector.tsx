import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { fetchJson } from "../api";
import { SymbolsResponse } from "../types";

export function SymbolSelector({value, symbols, onChange}:{value:string;symbols:string[];onChange:(symbol:string)=>void}) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState(symbols);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const root = useRef<HTMLLabelElement>(null);
  useEffect(() => setQuery(value), [value]);
  useEffect(() => { if (!open || !query.trim()) { setResults([]); return; } const timer = setTimeout(() => { setLoading(true); fetchJson<SymbolsResponse>(`/api/symbols?query=${encodeURIComponent(query)}`).then((data) => { setResults(data.symbols || []); setHighlighted(0); }).catch(() => setResults([])).finally(() => setLoading(false)); }, 275); return () => clearTimeout(timer); }, [query, open]);
  useEffect(() => { const close = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); }; document.addEventListener("mousedown", close); return () => document.removeEventListener("mousedown", close); }, []);
  const choose = (symbol: string) => { setQuery(symbol); setOpen(false); onChange(symbol); };
  return <label className="symbol-select" ref={root}><span>ИНСТРУМЕНТ</span><input className="symbol-search" role="combobox" aria-expanded={open} value={query} onChange={(e) => { setQuery(e.target.value.toUpperCase()); setOpen(true); }} onFocus={() => setOpen(true)} onKeyDown={(e) => { if (e.key === "Escape") { setOpen(false); return; } if (!open || !results.length) return; if (e.key === "ArrowDown") { e.preventDefault(); setHighlighted((index) => Math.min(index + 1, results.length - 1)); } if (e.key === "ArrowUp") { e.preventDefault(); setHighlighted((index) => Math.max(index - 1, 0)); } if (e.key === "Enter") { e.preventDefault(); choose(results[highlighted]); } }}/><ChevronDown size={14}/>{open && <span className="symbol-results">{loading ? <span className="symbol-result-state">Загрузка…</span> : results.length ? results.slice(0, 20).map((symbol, index) => <button type="button" className={index === highlighted ? "highlighted" : ""} key={symbol} onMouseDown={() => choose(symbol)}>{symbol}</button>) : <span className="symbol-result-state">Ничего не найдено</span>}</span>}</label>;
}
