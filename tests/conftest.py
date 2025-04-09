import pytest
from moccasin.config import get_active_network
from src.mocks import mock_vrf_coordinator
from src import raffle
import boa

@pytest.fixture(scope="session")
def account():
    acct = get_active_network().get_default_account()
    boa.env.set_balance(acct.address, 10**18)  # 1 ETH
    return acct

@pytest.fixture(scope="session")
def mock_vrf():
    mock = mock_vrf_coordinator.deploy()
    # Add mock implementation for fulfillRandomWords
    def fulfill_random_words(request_id: int, random_words: list):
        raffle_address = mock.requestIdToRaffle(request_id)
        raffle_contract = boa.load_partial(raffle.vy).at(raffle_address)
        raffle_contract.fulfill_random_words(request_id, random_words)
    
    mock.fulfill_random_words = fulfill_random_words
    return mock

@pytest.fixture(scope="session")
def raffle_contract(mock_vrf):
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
    
    # Store raffle address in mock for callback
    mock_vrf.raffle_address = raffle_instance.address
    return raffle_instance