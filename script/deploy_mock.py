from moccasin.boa_tools import VyperContract
from src.mocks import mock_vrf_coordinator 

def deploy_mock() -> VyperContract:
    mock = mock_vrf_coordinator.deploy()
    print(f"Mock VRF Coordinator at: {mock.address}")
    return mock.address

def moccasin_main() -> VyperContract:
    return deploy_mock()