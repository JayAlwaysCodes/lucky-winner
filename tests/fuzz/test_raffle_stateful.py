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
            10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000
        )
        self.players = {}

    @rule(sender=st.sampled_from([boa.env.generate_address() for _ in range(5)]))  # Fix address generation
    def enter_raffle(self, sender):
        if self.raffle.get_raffle_state() != 0:
            return
        with boa.env.prank(sender):  # Use prank instead of set_sender
            entrance_fee = self.raffle.get_entrance_fee()
            try:
                self.raffle.enter_raffle(value=entrance_fee)
                self.players[sender] = self.players.get(sender, 0) + entrance_fee
            except Exception:
                pass

    @rule()
    def request_winner(self):
        if self.raffle.get_raffle_state() != 0 or self.raffle.get_player_count() == 0:
            return
        boa.env.increase_time(61)
        sender = boa.env.generate_address()
        with boa.env.prank(sender):  # Use prank here too
            try:
                self.raffle.request_winner()
                self.players = {}
            except Exception:
                pass

    @invariant()
    def check_state(self):
        state = self.raffle.get_raffle_state()
        assert state in [0, 1], f"Invalid raffle state: {state}"
        if state == 0:
            assert self.raffle.get_player_count() <= len(self.players)
        elif state == 1:
            assert self.raffle.get_player_count() > 0

TestRaffleState = RaffleStateMachine.TestCase