import time
from unittest.mock import MagicMock

import pytest

from nautilus_trader.adapters.polymarket.providers import PolymarketInstrumentProvider
from nautilus_trader.common.component import LiveClock
from nautilus_trader.model.identifiers import InstrumentId


@pytest.fixture
def mock_clob_client_delayed():
    client = MagicMock()

    def delayed_get_market(condition_id):
        time.sleep(0.1)
        return {
            "condition_id": condition_id,
            "active": True,
            "closed": False,
            "tokens": [{"token_id": "123", "outcome": "Yes"}, {"token_id": "456", "outcome": "No"}],
        }

    client.get_market.side_effect = delayed_get_market
    return client


@pytest.mark.asyncio
async def test_load_markets_seq_concurrency(mock_clob_client_delayed):
    provider = PolymarketInstrumentProvider(
        client=mock_clob_client_delayed,
        clock=LiveClock(),
    )

    ids = []
    for i in range(5):
        cond = f"0x{i:064d}"
        tok = "123"
        ids.append(InstrumentId.from_str(f"{cond}-{tok}.POLYMARKET"))

    start = time.perf_counter()
    await provider._load_markets_seq(ids)
    end = time.perf_counter()

    duration = end - start

    # 5 requests * 0.1s = 0.5s if sequential.
    # Should be ~0.1s + overhead if concurrent.
    assert duration < 0.4, f"Expected < 0.4s (concurrent), got {duration:.2f}s"
