from recorder.bybit.private_collector import build_private_collector
from recorder.bybit.public_collector import build_public_collector


def test_public_topics_are_config_driven(tmp_path):
    collector = build_public_collector(["SUIUSDT", "ETHUSDT"], ["1", "15"], False, None, None)
    assert "kline.1.SUIUSDT" in collector.topics
    assert "tickers.ETHUSDT" in collector.topics
    assert collector.url == "wss://stream.bybit.com/v5/public/linear"


def test_private_collector_has_only_observation_topics(tmp_path):
    collector = build_private_collector("key", "secret", True, None, None)
    assert set(collector.topics) == {"order", "execution", "position", "wallet"}
    assert collector.url == "wss://stream-testnet.bybit.com/v5/private"
