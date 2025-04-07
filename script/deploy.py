from moccasin.boa_tools import VyperContract
from eth_account import Account
from src.mocks import mock_vrf_coordinator
from src import raffle
import os

def deploy() -> VyperContract:
    
    # Deploy mock first
    mock = mock_vrf_coordinator.deploy()
    vrf_coordinator = mock.address
    print(f"Mock VRF Coordinator at: {vrf_coordinator}")

    # Raffle parameters (example values, adjust as needed)
    entrance_fee =  10**16  # 0.01 ETH in wei
    interval = 3600  # 1 hour in seconds
    gas_lane = b"\x00" * 32 # Replace with actual key hash (32 bytes)
    subscription_id = 1234  # Replace with your Chainlink subscription ID
    callback_gas_limit = 100000  # Gas limit for VRF callback
    
    print(f"entrance_fee: {entrance_fee}, type: {type(entrance_fee)}")
    print(f"interval: {interval}, type: {type(interval)}")
    print(f"subscription_id: {subscription_id}, type: {type(subscription_id)}")
    print(f"callback_gas_limit: {callback_gas_limit}, type: {type(callback_gas_limit)}")

    # Deploy the contract
    raffle_contract = raffle.deploy(
        
        entrance_fee,
        interval,
        vrf_coordinator,
        gas_lane,
        subscription_id,
        callback_gas_limit,
    )

    print(f"Raffle deployed at: {raffle_contract.address}")
    return raffle_contract

def moccasin_main() -> VyperContract:
    return deploy()