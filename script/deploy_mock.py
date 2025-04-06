from src.mocks import mock_vrf_coordinator 

def deploy_mock():
    mock = mock_vrf_coordinator.deploy("mock_vrf_coordinator")
    print(f"Mock VRF Coordinator at: {mock.address}")
    return mock.address