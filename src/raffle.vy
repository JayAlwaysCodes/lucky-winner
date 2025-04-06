# pragma version 0.4.0
"""
@title Raffle
@license MIT
@notice A raffle contract using Chainlink VRF 2.5 for secure randomness
"""

# Chainlink VRF Coordinator interface (simplified for Vyper)
interface VRFCoordinatorV2_5:
    def requestRandomWords(
        keyHash: bytes32,
        subId: uint64,
        requestConfirmations: uint16,
        callbackGasLimit: uint32,
        numWords: uint32
    ) -> uint256: nonpayable

# Constants
REQUEST_CONFIRMATIONS: constant(uint16) = 3
NUM_WORDS: constant(uint32) = 1
RAFFLE_STATE_OPEN: constant(uint256) = 0
RAFFLE_STATE_CALCULATING: constant(uint256) = 1

# Immutable config (set at deployment)
entrance_fee: immutable(uint256)
interval: immutable(uint256)  # Duration in seconds
vrf_coordinator: immutable(VRFCoordinatorV2_5)
gas_lane: immutable(bytes32)  # Key hash for VRF
subscription_id: immutable(uint64)  # Chainlink subscription ID
callback_gas_limit: immutable(uint32)

# State variables
players: public(HashMap[uint256, address])  # Player index -> address
player_count: public(uint256)  # Total number of players
last_timestamp: public(uint256)  # Last raffle reset time
recent_winner: public(address)  # Most recent winner
raffle_state: public(uint256)  # 0 = OPEN, 1 = CALCULATING

@deploy
@payable
def __init__(
    _entrance_fee: uint256,
    _interval: uint256,
    _vrf_coordinator: address,
    _gas_lane: bytes32,
    _subscription_id: uint64,
    _callback_gas_limit: uint32
):
    """
    @notice Initialize the raffle contract
    @param _entrance_fee Minimum ETH to enter (in wei)
    @param _interval Duration of raffle in seconds
    @param _vrf_coordinator Chainlink VRF Coordinator address
    @param _gas_lane Gas lane key hash for VRF
    @param _subscription_id Chainlink subscription ID
    @param _callback_gas_limit Gas limit for VRF callback
    """
    entrance_fee = _entrance_fee
    interval = _interval
    vrf_coordinator = VRFCoordinatorV2_5(_vrf_coordinator)
    gas_lane = _gas_lane
    subscription_id = _subscription_id
    callback_gas_limit = _callback_gas_limit
    self.raffle_state = RAFFLE_STATE_OPEN
    self.last_timestamp = block.timestamp

@external
@payable
def enter_raffle():
    """
    @notice Enter the raffle by paying the entrance fee
    """
    assert msg.value >= entrance_fee, "Not enough ETH sent"
    assert self.raffle_state == RAFFLE_STATE_OPEN, "Raffle not open"
    self.players[self.player_count] = msg.sender
    self.player_count += 1

@external
def request_winner():
    """
    @notice Request a random winner (anyone can call after interval)
    """
    assert (block.timestamp - self.last_timestamp) >= interval, "Time interval not passed"
    assert self.raffle_state == RAFFLE_STATE_OPEN, "Raffle not open"
    assert self.player_count > 0, "No players in raffle"
    assert self.balance > 0, "No ETH in contract"

    self.raffle_state = RAFFLE_STATE_CALCULATING
    request_id: uint256 = extcall vrf_coordinator.requestRandomWords(
        gas_lane,
        subscription_id,
        REQUEST_CONFIRMATIONS,
        callback_gas_limit,
        NUM_WORDS
    )
    log RequestedWinner(request_id)

@external
@nonreentrant
def fulfill_random_words(request_id: uint256, random_words: DynArray[uint256, 1]):
    """
    @notice Chainlink VRF callback to pick and pay the winner
    @dev Called by VRF Coordinator, must be public and match signature
    """
    assert self.raffle_state == RAFFLE_STATE_CALCULATING, "Not calculating winner"
    winner_index: uint256 = random_words[0] % self.player_count
    winner: address = self.players[winner_index]
    self.recent_winner = winner
    self.raffle_state = RAFFLE_STATE_OPEN
    self.last_timestamp = block.timestamp
    self.player_count = 0  # Reset players

    # Send prize
    send(winner, self.balance)
    log PickedWinner(winner)
# Getter functions
@external
@view
def get_entrance_fee() -> uint256:
    return entrance_fee

@external
@view
def get_raffle_state() -> uint256:
    return self.raffle_state

@external
@view
def get_player(index: uint256) -> address:
    return self.players[index]

@external
@view
def get_recent_winner() -> address:
    return self.recent_winner

@external
@view
def get_player_count() -> uint256:
    return self.player_count

@external
@view
def get_last_timestamp() -> uint256:
    return self.last_timestamp

# Events
event RequestedWinner:
    request_id: indexed(uint256)

event PickedWinner:
    winner: indexed(address)