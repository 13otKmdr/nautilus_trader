import asyncio
from decimal import Decimal
from functools import partial
import pytest
from ibapi.order_state import OrderState as IBOrderState
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.identifiers import PositionId
from nautilus_trader.test_kit.stubs.commands import TestCommandStubs
from nautilus_trader.test_kit.stubs.execution import TestExecStubs
from tests.integration_tests.adapters.interactive_brokers.test_kit import IBTestContractStubs
from tests.integration_tests.adapters.interactive_brokers.test_kit import IBTestExecStubs

@pytest.fixture
def contract_details():
    return IBTestContractStubs.aapl_equity_ib_contract_details()

@pytest.fixture
def contract(contract_details):
    return IBTestContractStubs.aapl_equity_ib_contract()

def instrument_setup(exec_client, cache, instrument=None, contract_details=None):
    instrument = instrument or IBTestContractStubs.aapl_instrument()
    contract_details = contract_details or IBTestContractStubs.aapl_equity_contract_details()
    exec_client._instrument_provider.contract_details[instrument.id] = contract_details
    exec_client._instrument_provider.contract_id_to_instrument_id[
        contract_details.contract.conId
    ] = instrument.id
    exec_client._instrument_provider.add(instrument)
    cache.add_instrument(instrument)

def on_open_order_setup(exec_client, client, status, order_id, contract, order):
    order_state = IBOrderState()
    order_state.status = status
    order_ref = order.orderRef.rsplit(":", 1)[0] if ":" in order.orderRef else order.orderRef
    exec_client._on_open_order(
        order_ref=order_ref,
        order=order,
        order_state=order_state,
    )

@pytest.mark.asyncio
async def test_order_filled_without_exec_details(
    mocker,
    exec_client,
    cache,
    instrument,
    contract_details,
    client_order_id,
    mock_connection_setup,
):
    # Arrange
    instrument_setup(
        exec_client=exec_client,
        cache=cache,
        instrument=instrument,
        contract_details=contract_details,
    )
    # Setup connection mocks
    mock_connection_setup()
    exec_client.connect()
    await asyncio.sleep(0.1)

    mocker.patch.object(
        exec_client._client._eclient,
        "placeOrder",
        side_effect=partial(on_open_order_setup, exec_client, exec_client._client, "Submitted"),
    )
    order = TestExecStubs.limit_order(
        instrument=instrument,
        client_order_id=client_order_id,
    )
    cache.add_order(order, None)
    command = TestCommandStubs.submit_order_command(order=order)
    exec_client.submit_order(command=command)
    await asyncio.sleep(0)

    # Act
    # Send order status "Filled" but NO execDetails
    exec_client._on_order_status(
        order_ref=str(client_order_id),
        order_status="Filled",
        avg_fill_price=100.0,
        filled=Decimal(100),
        remaining=Decimal(0),
    )
    await asyncio.sleep(0)

    # Assert
    # Without the fix, this should fail (Order status remains ACCEPTED/SUBMITTED)
    assert cache.order(client_order_id).status == OrderStatus.FILLED
