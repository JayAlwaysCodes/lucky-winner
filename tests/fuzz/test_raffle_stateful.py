from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from hypothesis import strategies as st
from src.mocks import mock_vrf_coordinator
from src import raffle
import boa

class RaffleStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(
            10**16,  # 0.01 ETH
            60,      # 60 seconds
            self.mock.address,
            b"\x00" * 32,
            1234,
            100000
        )
        self.players = {}  # Tracks entered addresses and their balances

    @rule(sender=st.sampled_from(boa.env.generate_addresses(5)))
    def enter_raffle(self, sender):
        """Simulate a user entering the raffle."""
        if self.raffle.get_raffle_state() != 0:  # Only if OPEN
            return
        boa.env.set_sender(sender)
        entrance_fee = self.raffle.get_entrance_fee()
        try:
            self.raffle.enter_raffle(value=entrance_fee)
            self.players[sender] = self.players.get(sender, 0) + entrance_fee
        except Exception:
            pass  # Ignore failures (e.g., insufficient funds)

    @rule()
    def request_winner(self):
        """Simulate requesting a winner after interval."""
        if self.raffle.get_raffle_state() != 0 or self.raffle.get_player_count() == 0:
            return
        boa.env.increase_time(61)  # Pass interval
        boa.env.set_sender(boa.env.generate_address())
        try:
            self.raffle.request_winner()
            self.players = {}  # Reset tracked players after winner picked
        except Exception:
            pass

    @invariant()
    def check_state(self):
        """Ensure raffle state is consistent."""
        state = self.raffle.get_raffle_state()
        assert state in [0, 1], f"Invalid raffle state: {state}"
        if state == 0:  # OPEN
            assert self.raffle.get_player_count() <= len(self.players)
        elif state == 1:  # CALCULATING
            assert self.raffle.get_player_count() > 0

TestRaffleState = RaffleStateMachine.TestCase