import pytest
import boa

def test_enter_raffle(raffle_contract, account):
    """Test that a user can enter the raffle with the correct entrance fee."""
    # Set the sender to the test account
    boa.env._get_sender(account.address)
    
    # Enter the raffle
    entrance_fee = raffle_contract.get_entrance_fee()
    tx = raffle_contract.enter_raffle(value=entrance_fee)
    
    # Verify player count increased
    assert raffle_contract.get_player_count() == 1
    assert raffle_contract.get_player(0) == account.address
    assert tx.events["EnteredRaffle"][0]["player"] == account.address

def test_enter_raffle_insufficient_funds(raffle_contract, account):
    """Test that entering with insufficient funds reverts."""
    boa.env._get_sender(account.address)
    entrance_fee = raffle_contract.get_entrance_fee()
    
    with pytest.raises(Exception, match="Not enough ETH sent"):
        raffle_contract.enter_raffle(value=entrance_fee // 2)

def test_request_winner(raffle_contract, account):
    """Test requesting a winner after entering the raffle."""
    boa.env.set_sender(account.address)
    
    # Enter the raffle
    entrance_fee = raffle_contract.get_entrance_fee()
    raffle_contract.enter_raffle(value=entrance_fee)
    
    # Fast-forward time to pass the interval
    boa.env.increase_time(61)  # 60-second interval + 1
    
    # Request winner
    tx = raffle_contract.request_winner()
    
    # Verify winner was picked (mock VRF calls back immediately)
    assert raffle_contract.get_recent_winner() == account.address
    assert raffle_contract.get_player_count() == 0  # Reset after winner picked
    assert tx.events["PickedWinner"][0]["winner"] == account.address