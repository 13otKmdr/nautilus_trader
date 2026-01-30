from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pandas as pd
import pytest

from nautilus_trader.adapters.interactive_brokers.config import (
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.adapters.interactive_brokers.providers import (
    InteractiveBrokersInstrumentProvider,
)
from nautilus_trader.common.component import LiveClock
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog.base import BaseDataCatalog
from tests.integration_tests.adapters.interactive_brokers.test_kit import IBTestContractStubs


@pytest.mark.asyncio
async def test_provider_loads_valid_cached_instrument(mocker):
    # Mock dependencies
    client = MagicMock()
    client._cache = MagicMock()
    client._cache.instrument.return_value = None  # Initially not in client cache

    clock = LiveClock()

    # Mock Catalog
    catalog = MagicMock(spec=BaseDataCatalog)

    # Create a valid instrument
    instrument = IBTestContractStubs.aapl_instrument()

    # Set ts_event to recent (within 1 day)
    now = clock.utc_now()
    instrument.ts_event = (now - pd.Timedelta(hours=1)).value

    # Add contract info to instrument.info
    details = IBTestContractStubs.aapl_equity_contract_details()
    # Manually construct dict since IBContractDetails is a config object
    # We need a dict that dict_to_contract_details can parse back
    details_dict = {
        "contract": {
            "conId": details.contract.conId,
            "secType": details.contract.secType,
            "symbol": details.contract.symbol,
            "exchange": details.contract.exchange,
            "currency": details.contract.currency,
        },
        "minTick": details.minTick,
        "priceMagnifier": details.priceMagnifier,
        "marketName": details.marketName,
        "tradingHours": details.tradingHours,
        "liquidHours": details.liquidHours,
        "timeZoneId": details.timeZoneId,
    }

    instrument.info = details_dict

    # Configure catalog to return this instrument
    catalog.instruments.return_value = [instrument]

    # Configure config
    instrument_id_str = "AAPL.NASDAQ"
    config = InteractiveBrokersInstrumentProviderConfig(
        load_ids=[instrument_id_str],
        cache_validity_days=1,
    )

    provider = InteractiveBrokersInstrumentProvider(
        client=client,
        clock=clock,
        config=config,
        catalog=catalog,
    )

    # Mock load_ids_with_return_async to prevent actual loading attempts from IB if cache miss (though here we expect hit)
    # But wait, logic calls super().initialize() which calls load_ids_async.
    # If instrument is already loaded, load_ids_async calls load_with_return_async.
    # load_with_return_async calls fetch_instrument_id.
    # fetch_instrument_id checks self.contract.
    # If self.contract is populated, it returns True immediately.
    # So we don't need to mock load_ids_with_return_async if everything works correctly.
    # But to be safe and isolate "loading from IB", we can spy on it.

    spy_fetch = mocker.spy(provider, "fetch_instrument_id")

    # Initialize
    await provider.initialize()

    # Verify
    catalog.instruments.assert_called_once_with(instrument_ids=[instrument_id_str])

    # Instrument should be loaded
    loaded_instrument = provider.find(InstrumentId.from_str(instrument_id_str))
    assert loaded_instrument is not None
    assert loaded_instrument == instrument

    # Contract details should be populated
    assert provider.contract_details[loaded_instrument.id] is not None
    assert provider.contract[loaded_instrument.id] is not None

    # Check that fetch_instrument_id found it in memory (contract map)
    # fetch_instrument_id is called by load_ids_async -> load_with_return_async
    # It should return True without calling client.get_contract_details
    assert spy_fetch.call_count > 0
    # And client.get_contract_details should NOT be called
    client.get_contract_details.assert_not_called()


@pytest.mark.asyncio
async def test_provider_skips_expired_cached_instrument(mocker):
    # Mock dependencies
    client = MagicMock()
    client._cache = MagicMock()

    clock = LiveClock()
    catalog = MagicMock(spec=BaseDataCatalog)

    # Create an expired instrument
    instrument = IBTestContractStubs.aapl_instrument()

    # Set ts_event to old (older than 1 day)
    now = clock.utc_now()
    instrument.ts_event = (now - pd.Timedelta(days=2)).value

    details = IBTestContractStubs.aapl_equity_contract_details()
    details_dict = {
        "contract": {
            "conId": details.contract.conId,
            "secType": details.contract.secType,
            "symbol": details.contract.symbol,
            "exchange": details.contract.exchange,
            "currency": details.contract.currency,
        },
        "minTick": details.minTick,
    }
    instrument.info = details_dict

    catalog.instruments.return_value = [instrument]

    # Configure config
    instrument_id_str = "AAPL.NASDAQ"
    config = InteractiveBrokersInstrumentProviderConfig(
        load_ids=[instrument_id_str],
        cache_validity_days=1,
    )

    provider = InteractiveBrokersInstrumentProvider(
        client=client,
        clock=clock,
        config=config,
        catalog=catalog,
    )

    # Mock load_ids_with_return_async to prevent actual loading attempts from IB
    provider.load_ids_with_return_async = AsyncMock()

    await provider.initialize()

    # Verify catalog was queried
    catalog.instruments.assert_called_once()

    # Instrument should NOT be loaded (from cache)
    assert provider.find(InstrumentId.from_str(instrument_id_str)) is None
