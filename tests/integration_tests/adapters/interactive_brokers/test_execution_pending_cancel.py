# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import asyncio
from decimal import Decimal
from functools import partial

import pytest
from ibapi.order_state import OrderState as IBOrderState

from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.identifiers import PositionId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import Price
from nautilus_trader.test_kit.stubs.commands import TestCommandStubs
from nautilus_trader.test_kit.stubs.execution import TestExecStubs
from tests.integration_tests.adapters.interactive_brokers.test_kit import IBTestContractStubs
from tests.integration_tests.adapters.interactive_brokers.test_kit import IBTestDataStubs


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


def account_summary_setup(client, **kwargs):
    account_values = IBTestDataStubs.account_values()
    for summary in account_values:
        client.accountSummary(
            req_id=kwargs["reqId"],
            account=summary["account"],
            tag=summary["tag"],
            value=summary["value"],
            currency=summary["currency"],
        )


def on_open_order_setup(exec_client, client, status, order_id, contract, order):
    """
    Directly call the handler, bypassing the message queue.
    """
    order_state = IBOrderState()
    order_state.status = status
    # Extract order_ref from the order to match what the handler expects
    order_ref = order.orderRef.rsplit(":", 1)[0] if ":" in order.orderRef else order.orderRef
    # Call the handler directly on the execution client
    exec_client._on_open_order(
        order_ref=order_ref,
        order=order,
        order_state=order_state,
    )


@pytest.mark.asyncio
async def test_pending_cancel_order(
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

    # We create an order and submit it
    order = TestExecStubs.limit_order(
        instrument=instrument,
        client_order_id=client_order_id,
        price=Price.from_int(90),
    )
    cache.add_order(order, None)
    command = TestCommandStubs.submit_order_command(order=order)
    exec_client.submit_order(command=command)
    await asyncio.sleep(0)

    # Verify it is accepted (due to placeOrder mock triggering Submitted -> Accepted logic in exec client)
    assert cache.order(client_order_id).status == OrderStatus.ACCEPTED

    # Act
    # Simulate PendingCancel status update from IB
    # We use _on_order_status directly

    # Need to get venue_order_id. It should have been set by _on_open_order handling
    venue_order_id = cache.order(client_order_id).venue_order_id
    assert venue_order_id is not None

    exec_client._on_order_status(
        order_ref=str(client_order_id),
        order_status="PendingCancel",
        avg_fill_price=0.0,
        filled=Decimal(0),
        remaining=Decimal(100),
        venue_order_id=venue_order_id,
    )
    await asyncio.sleep(0)

    # Assert
    # The cache should be updated to PENDING_CANCEL if the event was generated and handled correctly
    assert cache.order(client_order_id).status == OrderStatus.PENDING_CANCEL
