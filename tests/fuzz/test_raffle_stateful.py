from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition
from hypothesis import strategies as st
from moccasin.boa_tools import VyperContract
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

    @rule(sender=st.sampled_from([boa.env.generate_address() for _ in range(5)]))
    def enter_raffle(self, sender):
        if self.raffle.get_raffle_state() != 0:
            return
        with boa.env.prank(sender):
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
        boa.env.time_travel(seconds=61)
        sender = boa.env.generate_address()
        with boa.env.prank(sender):
            try:
                self.raffle.request_winner()
                request_id = self.mock.last_request_id()
                self.mock.callBackWithRandomness(123)
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

class MultiPlayerRaffleMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(
            10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000
        )
        self.entries = []
        self.current_time = self.raffle.get_last_timestamp()

    @rule(sender=st.sampled_from([boa.env.generate_address() for _ in range(5)]))
    def enter_raffle(self, sender):
        if self.raffle.get_raffle_state() != 0:
            return
        entrance_fee = self.raffle.get_entrance_fee()
        boa.env.set_balance(sender, entrance_fee * 2)
        with boa.env.prank(sender):
            try:
                self.raffle.enter_raffle(value=entrance_fee)
                self.entries.append(sender)
            except Exception:
                pass

    @rule()
    def request_winner(self):
        if self.raffle.get_raffle_state() != 0 or self.raffle.get_player_count() == 0:
            return
        time_passed = self.current_time - self.raffle.get_last_timestamp()
        if time_passed < 60:
            seconds_to_travel = 60 - time_passed + 1
            boa.env.time_travel(seconds=seconds_to_travel)
            self.current_time += seconds_to_travel
        sender = boa.env.generate_address()
        with boa.env.prank(sender):
            try:
                self.raffle.request_winner()
                request_id = self.mock.last_request_id()
                random_value = st.integers(min_value=0, max_value=1000).example()
                with boa.env.prank(self.mock.address):
                    self.raffle.fulfill_random_words(request_id, [random_value])
                self.entries = []
            except Exception:
                pass

    @invariant()
    def check_state_consistency(self):
        state = self.raffle.get_raffle_state()
        assert state in [0, 1], "Invalid raffle state"
        if state == 0:
            assert self.raffle.get_player_count() == len(self.entries), "Player count mismatch"
        elif state == 1:
            assert self.raffle.get_player_count() > 0

class TimeStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000)
        self.player = boa.env.generate_address()
        boa.env.set_balance(self.player, 10**18)
        self.current_time = self.raffle.get_last_timestamp()

    @rule(amount=st.integers(min_value=0, max_value=10**17))
    def enter_with_varying_amounts(self, amount):
        if self.raffle.get_raffle_state() != 0:
            return
        # Ensure player has enough ETH for amount + gas
        boa.env.set_balance(self.player, amount + 10**16)  # Extra 0.01 ETH for gas
        with boa.env.prank(self.player):
            try:
                self.raffle.enter_raffle(value=amount)
                assert amount >= 10**16, "Should have reverted for insufficient funds"
            except Exception as e:
                assert amount < 10**16, f"Should have succeeded with sufficient funds, got {str(e)}"

    @rule(seconds=st.integers(min_value=0, max_value=120))
    def time_travel_and_request(self, seconds):
        if self.raffle.get_player_count() == 0 or self.raffle.get_raffle_state() != 0:
            return
        boa.env.time_travel(seconds=seconds)
        self.current_time += seconds
        with boa.env.prank(self.player):
            try:
                self.raffle.request_winner()
                if seconds < 60:
                    assert False, "Should have reverted - too soon"
                request_id = self.mock.last_request_id()
                with boa.env.prank(self.mock.address):
                    self.raffle.fulfill_random_words(request_id, [42])
            except Exception:
                if seconds >= 60:
                    assert False, "Should have succeeded after interval"

    @invariant()
    def check_time_state(self):
        state = self.raffle.get_raffle_state()
        if state == 0 and self.raffle.get_player_count() > 0:
            time_since = self.current_time - self.raffle.get_last_timestamp()
            assert time_since >= 0, "Timestamp should never go backwards"

class VRFStressMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000)
        self.players = [boa.env.generate_address() for _ in range(3)]
        for p in self.players:
            boa.env.set_balance(p, 10**18)

    @rule(player=st.sampled_from([0, 1, 2]))
    def enter_raffle(self, player):
        if self.raffle.get_raffle_state() != 0:
            return
        with boa.env.prank(self.players[player]):
            self.raffle.enter_raffle(value=10**16)

    @precondition(lambda self: self.raffle.get_player_count() > 0)
    @rule(random_value=st.integers(min_value=0, max_value=1000))
    def trigger_vrf(self, random_value):
        if self.raffle.get_raffle_state() != 0:
            return
        boa.env.time_travel(seconds=61)
        with boa.env.prank(self.players[0]):
            self.raffle.request_winner()
        request_id = self.mock.last_request_id()
        with boa.env.prank(self.mock.address):
            try:
                self.raffle.fulfill_random_words(request_id, [random_value])
                winner = self.raffle.get_recent_winner()
                assert winner in self.players, "Winner should be one of the players"
            except Exception:
                pass

    @rule(bogus_id=st.integers(min_value=0, max_value=1000000))
    def bogus_vrf_call(self, bogus_id):
        if self.raffle.get_raffle_state() == 0:
            return
        with boa.env.prank(self.mock.address):
            try:
                self.raffle.fulfill_random_words(bogus_id, [42])
                assert bogus_id == self.mock.last_request_id(), "Should fail unless ID matches"
            except Exception:
                pass

    @invariant()
    def check_vrf_state(self):
        if self.raffle.get_raffle_state() == 1:
            assert self.raffle.get_player_count() > 0, "Calculating state requires players"

TestRaffleState = RaffleStateMachine.TestCase
TestMultiPlayerRaffle = MultiPlayerRaffleMachine.TestCase
TestTimeState = TimeStateMachine.TestCase
TestVRFStress = VRFStressMachine.TestCase