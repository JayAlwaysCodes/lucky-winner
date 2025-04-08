import pytest
from moccasin.config import get_active_network
from src.mocks import mock_vrf_coordinator
from src import raffle

@pytest.fixture(scope="session")
def account():
    """Returns the default account from the active network (e.g., Anvil's first account)."""
    return get_active_network().get_default_account()

@pytest.fixture(scope="session")
def mock_vrf():
    """Deploys and returns the mock VRF Coordinator contract."""
    mock = mock_vrf_coordinator.deploy()
    return mock

@pytest.fixture(scope="session")
def raffle_contract(mock_vrf):
    """Deploys and returns the raffle contract with mock VRF Coordinator."""
    entrance_fee = 10**16  # 0.01 ETH in wei
    interval = 60  # 60 seconds for testing
    vrf_coordinator = mock_vrf.address
    gas_lane = b"\x00" * 32
    subscription_id = 1234
    callback_gas_limit = 100000

    raffle_instance = raffle.deploy(
        entrance_fee,
        interval,
        vrf_coordinator,
        gas_lane,
        subscription_id,
        callback_gas_limit
    )
    return raffle_instance