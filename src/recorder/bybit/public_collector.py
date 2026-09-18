from recorder.bybit.ws_common import BybitWebSocketCollector


def build_public_collector(
    symbols,
    intervals,
    testnet,
    raw_writer,
    on_event,
    session_store=None,
    category="linear",
    ticker=None,
    public_trades=False,
    orderbook=None,
    save_open_kline_updates_raw=True,
    **kwargs,
):
    host = "stream-testnet.bybit.com" if testnet else "stream.bybit.com"
    ticker = ticker or {"enabled": True}
    topics = [f"kline.{interval}.{symbol}" for symbol in symbols for interval in intervals]
    if ticker.get("enabled", True):
        topics.extend(f"tickers.{symbol}" for symbol in symbols)
    if public_trades:
        topics.extend(f"publicTrade.{symbol}" for symbol in symbols)
    if orderbook and orderbook.get("enabled"):
        topics.extend(f"orderbook.{orderbook['depth']}.{symbol}" for symbol in symbols)
    return BybitWebSocketCollector(
        f"wss://{host}/v5/public/{category}",
        "bybit_public",
        topics,
        raw_writer,
        on_event,
        session_store,
        sample_seconds=ticker.get("sample_interval_seconds", 1)
        if ticker.get("raw_recording") == "sampled"
        else 0,
        save_open_kline_updates_raw=save_open_kline_updates_raw,
        **kwargs,
    )
