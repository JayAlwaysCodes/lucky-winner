from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition
from hypothesis import strategies as st, settings, Phase, Verbosity
from moccasin.boa_tools import VyperContract
from src.mocks import mock_vrf_coordinator
from src import raffle
import boa
import pytest

class RaffleStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(
            10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000
        )
        self.players = {}
        print(f"\nStarting new {self.__class__.__name__} test")

    def print_step(self, step_name, **kwargs):
        print(f"Step: {step_name} - {' '.join(f'{k}={v}' for k, v in kwargs.items())}")

    @rule(sender=st.sampled_from([boa.env.generate_address() for _ in range(5)]))
    def enter_raffle(self, sender):
        self.print_step("enter_raffle", sender=sender)
        if self.raffle.get_raffle_state() != 0:
            print("  Skipped: Raffle not in open state")
            return
        with boa.env.prank(sender):
            entrance_fee = self.raffle.get_entrance_fee()
            try:
                self.raffle.enter_raffle(value=entrance_fee)
                self.players[sender] = self.players.get(sender, 0) + entrance_fee
                print(f"  Success: Player entered raffle with {entrance_fee}")
            except Exception as e:
                print(f"  Failed: {str(e)}")

    @rule()
    def request_winner(self):
        self.print_step("request_winner")
        if self.raffle.get_raffle_state() != 0 or self.raffle.get_player_count() == 0:
            print("  Skipped: Raffle not ready for winner selection")
            return
        boa.env.time_travel(seconds=61)
        sender = boa.env.generate_address()
        with boa.env.prank(sender):
            try:
                self.raffle.request_winner()
                request_id = self.mock.last_request_id()
                self.mock.callBackWithRandomness(123)
                self.players = {}
                print("  Success: Winner requested")
            except Exception as e:
                print(f"  Failed: {str(e)}")

    @invariant()
    def check_state(self):
        state = self.raffle.get_raffle_state()
        player_count = self.raffle.get_player_count()
        print(f"  Invariant check: state={state}, player_count={player_count}, tracked_players={len(self.players)}")
        assert state in [0, 1], f"Invalid raffle state: {state}"
        if state == 0:
            assert player_count <= len(self.players)
        elif state == 1:
            assert player_count > 0

class MultiPlayerRaffleMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(
            10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000
        )
        self.entries = []
        self.current_time = self.raffle.get_last_timestamp()
        print(f"\nStarting new {self.__class__.__name__} test")

    def print_step(self, step_name, **kwargs):
        print(f"Step: {step_name} - {' '.join(f'{k}={v}' for k, v in kwargs.items())}")

    @rule(sender=st.sampled_from([boa.env.generate_address() for _ in range(5)]))
    def enter_raffle(self, sender):
        self.print_step("enter_raffle", sender=sender)
        if self.raffle.get_raffle_state() != 0:
            print("  Skipped: Raffle not in open state")
            return
        entrance_fee = self.raffle.get_entrance_fee()
        boa.env.set_balance(sender, entrance_fee * 2)
        with boa.env.prank(sender):
            try:
                self.raffle.enter_raffle(value=entrance_fee)
                self.entries.append(sender)
                print(f"  Success: Player entered raffle with {entrance_fee}")
            except Exception as e:
                print(f"  Failed: {str(e)}")

    @rule(random_value=st.integers(min_value=0, max_value=100))
    def request_winner(self, random_value):
        self.print_step("request_winner", random_value=random_value)
        if self.raffle.get_raffle_state() != 0 or self.raffle.get_player_count() == 0:
            print("  Skipped: Raffle not ready for winner selection")
            return
        time_passed = self.current_time - self.raffle.get_last_timestamp()
        if time_passed < 60:
            seconds_to_travel = 60 - time_passed + 1
            boa.env.time_travel(seconds=seconds_to_travel)
            self.current_time += seconds_to_travel
            print(f"  Time travel: {seconds_to_travel} seconds")
        sender = boa.env.generate_address()
        with boa.env.prank(sender):
            try:
                self.raffle.request_winner()
                request_id = self.mock.last_request_id()
                print(f"  Request ID: {request_id}")
                with boa.env.prank(self.mock.address):
                    self.raffle.fulfill_random_words(request_id, [random_value])
                    print(f"  Random value provided: {random_value}")
                self.entries = []
                print("  Success: Winner selected")
            except Exception as e:
                print(f"  Failed: {str(e)}")

    @invariant()
    def check_state_consistency(self):
        state = self.raffle.get_raffle_state()
        player_count = self.raffle.get_player_count()
        print(f"  Invariant check: state={state}, player_count={player_count}, entries={len(self.entries)}")
        assert state in [0, 1], "Invalid raffle state"
        if state == 0:
            assert player_count == len(self.entries), "Player count mismatch"
        elif state == 1:
            assert player_count > 0

class TimeStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000)
        self.player = boa.env.generate_address()
        boa.env.set_balance(self.player, 10**18)
        self.current_time = self.raffle.get_last_timestamp()
        print(f"\nStarting new {self.__class__.__name__} test")

    def print_step(self, step_name, **kwargs):
        print(f"Step: {step_name} - {' '.join(f'{k}={v}' for k, v in kwargs.items())}")

    @rule(amount=st.integers(min_value=0, max_value=10**17))
    def enter_with_varying_amounts(self, amount):
        self.print_step("enter_with_varying_amounts", amount=amount)
        if self.raffle.get_raffle_state() != 0:
            print("  Skipped: Raffle not in open state")
            return
        # Ensure player has enough ETH for amount + gas
        boa.env.set_balance(self.player, amount + 10**16)  # Extra 0.01 ETH for gas
        with boa.env.prank(self.player):
            try:
                self.raffle.enter_raffle(value=amount)
                assert amount >= 10**16, "Should have reverted for insufficient funds"
                print(f"  Success: Player entered with {amount}")
            except Exception as e:
                assert amount < 10**16, f"Should have succeeded with sufficient funds, got {str(e)}"
                print(f"  Expected failure: {str(e)}")

    @rule(seconds=st.integers(min_value=0, max_value=120))
    def time_travel_and_request(self, seconds):
        self.print_step("time_travel_and_request", seconds=seconds)
        if self.raffle.get_player_count() == 0 or self.raffle.get_raffle_state() != 0:
            print("  Skipped: Raffle not ready for winner selection")
            return
        boa.env.time_travel(seconds=seconds)
        self.current_time += seconds
        print(f"  Time travel: {seconds} seconds")
        with boa.env.prank(self.player):
            try:
                self.raffle.request_winner()
                if seconds < 60:
                    assert False, "Should have reverted - too soon"
                request_id = self.mock.last_request_id()
                print(f"  Request ID: {request_id}")
                with boa.env.prank(self.mock.address):
                    self.raffle.fulfill_random_words(request_id, [42])
                print("  Success: Winner selected")
            except Exception as e:
                if seconds >= 60:
                    assert False, "Should have succeeded after interval"
                print(f"  Expected failure: {str(e)}")

    @invariant()
    def check_time_state(self):
        state = self.raffle.get_raffle_state()
        player_count = self.raffle.get_player_count()
        time_since = self.current_time - self.raffle.get_last_timestamp()
        print(f"  Invariant check: state={state}, player_count={player_count}, time_since={time_since}")
        if state == 0 and player_count > 0:
            assert time_since >= 0, "Timestamp should never go backwards"

class VRFStressMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.mock = mock_vrf_coordinator.deploy()
        self.raffle = raffle.deploy(10**16, 60, self.mock.address, b"\x00" * 32, 1234, 100000)
        self.players = [boa.env.generate_address() for _ in range(3)]
        for p in self.players:
            boa.env.set_balance(p, 10**18)
        print(f"\nStarting new {self.__class__.__name__} test")

    def print_step(self, step_name, **kwargs):
        print(f"Step: {step_name} - {' '.join(f'{k}={v}' for k, v in kwargs.items())}")

    @rule(player=st.sampled_from([0, 1, 2]))
    def enter_raffle(self, player):
        self.print_step("enter_raffle", player=player)
        if self.raffle.get_raffle_state() != 0:
            print("  Skipped: Raffle not in open state")
            return
        with boa.env.prank(self.players[player]):
            try:
                self.raffle.enter_raffle(value=10**16)
                print(f"  Success: Player {player} entered raffle")
            except Exception as e:
                print(f"  Failed: {str(e)}")

    @precondition(lambda self: self.raffle.get_player_count() > 0)
    @rule(random_value=st.integers(min_value=0, max_value=100))
    def trigger_vrf(self, random_value):
        self.print_step("trigger_vrf", random_value=random_value)
        if self.raffle.get_raffle_state() != 0:
            print("  Skipped: Raffle not in open state")
            return
        boa.env.time_travel(seconds=61)
        print("  Time travel: 61 seconds")
        with boa.env.prank(self.players[0]):
            try:
                self.raffle.request_winner()
                print("  Winner requested")
            except Exception as e:
                print(f"  Failed to request winner: {str(e)}")
                return
        
        request_id = self.mock.last_request_id()
        print(f"  Request ID: {request_id}")
        with boa.env.prank(self.mock.address):
            try:
                self.raffle.fulfill_random_words(request_id, [random_value])
                winner = self.raffle.get_recent_winner()
                print(f"  Winner selected: {winner}")
                assert winner in self.players, "Winner should be one of the players"
            except Exception as e:
                print(f"  Failed to fulfill: {str(e)}")

    @rule(bogus_id=st.integers(min_value=0, max_value=100))
    def bogus_vrf_call(self, bogus_id):
        self.print_step("bogus_vrf_call", bogus_id=bogus_id)
        if self.raffle.get_raffle_state() == 0:
            print("  Skipped: Raffle in open state")
            return
        with boa.env.prank(self.mock.address):
            try:
                self.raffle.fulfill_random_words(bogus_id, [42])
                actual_id = self.mock.last_request_id()
                print(f"  Fulfilled with bogus ID: {bogus_id}, actual ID: {actual_id}")
                assert bogus_id == actual_id, "Should fail unless ID matches"
            except Exception as e:
                print(f"  Expected failure: {str(e)}")

    @invariant()
    def check_vrf_state(self):
        state = self.raffle.get_raffle_state()
        player_count = self.raffle.get_player_count()
        print(f"  Invariant check: state={state}, player_count={player_count}")
        if state == 1:
            assert player_count > 0, "Calculating state requires players"

# Apply settings to each test case
TestRaffleState = settings(
    max_examples=10,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],
    deadline=None,
    verbosity=Verbosity.verbose
)(RaffleStateMachine).TestCase

TestMultiPlayerRaffle = settings(
    max_examples=10,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],
    deadline=None,
    verbosity=Verbosity.verbose
)(MultiPlayerRaffleMachine).TestCase

TestTimeState = settings(
    max_examples=10,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],
    deadline=None,
    verbosity=Verbosity.verbose
)(TimeStateMachine).TestCase

TestVRFStress = settings(
    max_examples=10,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],
    deadline=None,
    verbosity=Verbosity.verbose
)(VRFStressMachine).TestCase