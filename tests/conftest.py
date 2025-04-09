import pytest
from moccasin.config import get_config, get_active_network
from src.mocks import mock_vrf_coordinator
from src import raffle
import boa

@pytest.fixture(scope="session")
def network_setup():
    """Configure the environment based on the active network"""
    config = get_config()
    network_name = config.get_active_network.name
    if network_name == "anvil":
        # Fork Anvil chain (ensure Anvil is running)
        boa.env.fork(url=config.get_network("anvil").url)
        print(f"Running tests on Anvil at {config.get_network('anvil').url}")
    else:
        # Reset to in-memory pyevm
        boa.env.reset()
        print("Running tests on pyevm")
    return network_name

@pytest.fixture(scope="session")
def account(network_setup):
    """Get the default account for the active network"""
    acct = get_active_network().get_default_account()
    boa.env.set_balance(acct.address, 10**18)  # 1 ETH initial funding
    return acct

@pytest.fixture(scope="session")
def mock_vrf(network_setup):
    """Deploy the mock VRF coordinator"""
    mock = mock_vrf_coordinator.deploy()
    def fulfill_random_words(request_id: int, random_words: list):
        raffle_address = mock.requestIdToRaffle(request_id)
        raffle_contract = boa.load_partial(raffle.vy).at(raffle_address)
        raffle_contract.fulfill_random_words(request_id, random_words)
    mock.fulfill_random_words = fulfill_random_words
    return mock

@pytest.fixture(scope="session")
def raffle_contract(mock_vrf):
    """Deploy the raffle contract"""
    entrance_fee = 10**16  # 0.01 ETH
    interval = 60
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
    mock_vrf.raffle_address = raffle_instance.address
    return raffle_instance