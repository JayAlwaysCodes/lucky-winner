# @version ^0.4.0

interface VRFConsumer:
    def fulfill_random_words(requestId: uint256, randomWords: DynArray[uint256, 1]): nonpayable

@deploy
def __init__():
    pass

@external
def requestRandomWords(
    keyHash: bytes32,
    subId: uint64,
    requestConfirmations: uint16,
    callbackGasLimit: uint32,
    numWords: uint32
) -> uint256:
    # Simplified mock: return a fake request ID and call back immediately
    request_id: uint256 = block.timestamp
    random_words: DynArray[uint256, 1] = [convert(keccak256(convert(block.timestamp, bytes32)), uint256)]
    extcall VRFConsumer(msg.sender).fulfill_random_words(request_id, random_words)
    return request_id