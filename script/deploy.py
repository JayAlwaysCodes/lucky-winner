from moccasin.boa import VyperContract
from eth_account import Account
import os

def deploy() -> VyperContract:
    

    # Raffle parameters (example values, adjust as needed)
    entrance_fee = 0.01 * 10**18  # 0.01 ETH in wei
    interval = 3600  # 1 hour in seconds
    vrf_coordinator = "0xYourVRFCoordinatorAddress"  # Replace with actual address
    gas_lane = bytes.fromhex("4b09e658ed251bcafeebbc69400383d49f344ace09b9576fe248bb02c003fe9f")  # Replace with actual key hash (32 bytes)
    subscription_id = 1234  # Replace with your Chainlink subscription ID
    callback_gas_limit = 100000  # Gas limit for VRF callback

    # Deploy the contract
    raffle_contract = VyperContract.deploy(
        "raffle",
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