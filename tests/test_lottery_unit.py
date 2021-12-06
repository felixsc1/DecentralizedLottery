from brownie import network, config, exceptions
from scripts.deploy_lottery import deploy_lottery
from scripts.helpful_scripts import LOCAL_BLOCKCHAIN_ENVIRONMENTS, get_account, fund_with_link, get_contract
from web3 import Web3
import pytest


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # ARRANGE
    lottery = deploy_lottery()
    # ACT
    # In mock we defined 1 ETH = 2000 USD
    # Thus, 50 USD = 0.025 ETH
    expected_entrance_fee = Web3.toWei(0.025, "ether")
    entrance_fee = lottery.getEntranceFee()
    # ASSERT
    assert expected_entrance_fee == entrance_fee


def test_cant_enter_unless_started():
    # ARRANGE
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    # ACT / ASSERT
    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter(
            {"from": get_account(), "value": lottery.getEntranceFee()})


def test_can_start_and_enter_lottery():
    # ARRANGE
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    # ACT
    lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})
    # ASSERT
    assert lottery.players(0) == account


def test_can_end_lottery():
    # this will only test if the function runs and changes the lottery state.
    # ARRANGE
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    fund_with_link(lottery.address)
    lottery.endLottery({"from": account})
    assert lottery.lottery_state() == 2  # i.e. CALCULATING_WINNER


def test_can_pick_winner_correctly():
    # this will actually test if a winner receives the reward.
    # ARRANGE
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=1),
                  "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=2),
                  "value": lottery.getEntranceFee()})
    fund_with_link(lottery.address)
    transaction = lottery.endLottery({"from": account})
    request_id = transaction.events["RequestedRandomness"]["requestId"]
    STATIC_RNG = 777
    get_contract("vrf_coordinator").callBackWithRandomness(
        request_id, STATIC_RNG, lottery.address, {"from": account})
    # since 777 % 3 == 0, we expect player0, i.e. our account to be the winner
    assert lottery.recentWinner() == account
    # also check if lottery balance has been transferred
    assert lottery.balance() == 0
    starting_balance_of_account = account.balance()
    balance_of_lottery = lottery.balance()
    assert account.balance() == starting_balance_of_account + balance_of_lottery
