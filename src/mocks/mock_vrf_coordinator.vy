# @version ^0.4.0

interface VRFConsumer:
    def fulfill_random_words(requestId: uint256, randomWords: DynArray[uint256, 1]): nonpayable

# Store last request
last_request_id: public(uint256)
consumer_address: public(address)

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
    # Store request info instead of immediately calling back
    self.last_request_id = block.timestamp
    self.consumer_address = msg.sender
    return self.last_request_id

# Add manual callback method for testing
@external
def callBackWithRandomness(random_value: uint256):
    random_words: DynArray[uint256, 1] = [random_value]
    extcall VRFConsumer(self.consumer_address).fulfill_random_words(self.last_request_id, random_words)