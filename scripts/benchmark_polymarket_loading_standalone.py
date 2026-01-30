
import asyncio
import time
from dataclasses import dataclass
from typing import Any


# Mocks
@dataclass
class Symbol:
    value: str

@dataclass
class InstrumentId:
    symbol: Symbol

    @classmethod
    def from_str(cls, s):
        return cls(Symbol(s))

def get_polymarket_condition_id(instrument_id: InstrumentId) -> str:
    parts = instrument_id.symbol.value.split("-")
    return parts[0]

def _check_clob_response(response: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(response, str):
        raise ValueError(response)
    return response

class MockLogger:
    def warning(self, msg): pass
    def error(self, msg): pass
    def info(self, msg): pass

class MockClient:
    def get_market(self, condition_id):
        time.sleep(0.1)  # Simulate network latency
        return {
            "condition_id": condition_id,
            "active": True,
            "closed": False,
            "tokens": [
                {"token_id": "123", "outcome": "Yes"},
                {"token_id": "456", "outcome": "No"}
            ]
        }

class PolymarketInstrumentProvider:
    def __init__(self, client):
        self._client = client
        self._log = MockLogger()

    def _load_instrument(self, response, token_id, outcome):
        pass

    async def _load_markets_seq(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        filter_is_active = filters.get("is_active", False) if filters else False

        # Prepare tasks
        tasks = [
            asyncio.to_thread(
                self._client.get_market,
                condition_id=get_polymarket_condition_id(instrument_id),
            )
            for instrument_id in instrument_ids
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        # Process results
        for i, response in enumerate(results):
            instrument_id = instrument_ids[i]
            response = _check_clob_response(response)

            try:
                active = response["active"]
                closed = response["closed"]

                if filter_is_active and (not active or closed):
                    continue

                condition_id = response["condition_id"]
                if not condition_id:
                    self._log.warning(f"{instrument_id} was archived (no `condition_id`)")
                    continue  # Archived

                for token_info in response["tokens"]:
                    token_id = token_info["token_id"]
                    if not token_id:
                        self._log.warning(f"Market {condition_id} had an empty token")
                        continue
                    outcome = token_info["outcome"]
                    self._load_instrument(response, token_id, outcome)
                    self._log.info(f"Loaded instrument {instrument_id}")
            except ValueError as e:
                self._log.error(f"Unable to parse market: {e}, {response}")

async def main():
    client = MockClient()
    provider = PolymarketInstrumentProvider(client)

    # Generate 10 instrument IDs
    instrument_ids = [
        InstrumentId.from_str(f"condition_{i}-token_{i}.POLYMARKET")
        for i in range(10)
    ]

    print("Starting concurrent benchmark...")
    start = time.perf_counter()
    await provider._load_markets_seq(instrument_ids)
    end = time.perf_counter()
    print(f"Time taken: {end - start:.4f}s")

if __name__ == "__main__":
    asyncio.run(main())
