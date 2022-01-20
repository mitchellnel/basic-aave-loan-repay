from telnetlib import GA
from brownie import config, network, interface
from brownie.network import gas_price
from brownie.network.gas.strategies import LinearScalingStrategy
from scripts.get_weth import get_weth
from scripts.helpful_scripts import (
    FORKED_LOCAL_ENVIRONMENTS,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
)
from web3 import Web3

AMOUNT = Web3.toWei(0.1, "ether")


def aave_borrow():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]

    if (
        network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS
        or network.show_active() in FORKED_LOCAL_ENVIRONMENTS
    ):
        get_weth()

    lending_pool = get_lending_pool()

    # approve use of our ERC20 tokens
    approve_erc20(AMOUNT, lending_pool.address, erc20_address, account)

    # deposit to Aave
    print(f"Depositing {AMOUNT} ERC20 tokens to Aave Lending Pool ...")
    deposit_txn = lending_pool.deposit(
        erc20_address, AMOUNT, account.address, 0, {"from": account}
    )
    deposit_txn.wait(1)
    print(f"... Done! Funds deposited.\n")

    # work out how much we can borrow
    total_debt_eth, borrowable_eth = get_borrowable_data(lending_pool, account)

    # we want to borrow DAI using our ETH
    # work out 1 DAI in ETH
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )

    # we only want to borrow 90% of our capacity
    amount_dai_to_borrow = (1 / dai_eth_price) * (borrowable_eth * 0.90)
    print(f"We are going to borrow {amount_dai_to_borrow} DAI\n")

    # borrow from Aave
    dai_address = config["networks"][network.show_active()]["dai_token"]
    print(f"Borrowing {amount_dai_to_borrow} DAI from Aave ...")
    borrow_txn = lending_pool.borrow(
        dai_address,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_txn.wait(1)
    print(
        f"... Done! {account.address} has borrowed {amount_dai_to_borrow} from Aave.\n"
    )

    # work out how much we can borrow now
    total_debt_eth, borrowable_eth = get_borrowable_data(lending_pool, account)

    # now we repay Aave with our DAI
    repay_all(amount_dai_to_borrow, lending_pool, account)

    # work out how much we can borrow again
    total_debt_eth, borrowable_eth = get_borrowable_data(lending_pool, account)


def get_lending_pool():
    # use address provider to get the lending pool address
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )

    lending_pool_address = lending_pool_addresses_provider.getLendingPool()

    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool


def approve_erc20(amount, spender, erc20_address, account):
    """We call this to approve spender to utilise the specified amount of ERC20 tokens
    from account's wallet.
    """
    print(f"Approving {spender} to access {amount} of {account}'s ERC20 tokens ...")
    erc20_token = interface.IERC20(erc20_address)

    approve_txn = erc20_token.approve(spender, amount, {"from": account})
    approve_txn.wait(1)
    print(
        f"... Done! {spender} is approved to use {amount} of of {account}'s ERC20 tokens.\n"
    )


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrows_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    available_borrows_eth = Web3.fromWei(available_borrows_eth, "ether")

    print(f"You have {total_collateral_eth} worth of ETH deposited.")
    print(f"You have {total_debt_eth} worth of ETH borrowed.")
    print(f"You can borrow {available_borrows_eth} worth of ETH.\n")

    return (float(total_debt_eth), float(available_borrows_eth))


def get_asset_price(price_feed_address):
    price_feed = interface.IAggregatorV3(price_feed_address)
    latest_price = price_feed.latestRoundData()[1]
    converted_latest_price = Web3.fromWei(latest_price, "ether")
    print(f"The current DAI/ETH price is {converted_latest_price}\n")
    return float(converted_latest_price)


def repay_all(amount, lending_pool, account, use_weth=False):
    # approve use of tokens to pay back
    amount_wei = Web3.toWei(amount, "ether")

    if use_weth:
        erc_token_address = config["networks"][network.show_active()]["weth_token"]
    else:
        erc_token_address = config["networks"][network.show_active()]["dai_token"]

    approve_erc20(
        Web3.toWei(amount_wei, "ether"),
        lending_pool.address,
        erc_token_address,
        account,
    )

    print(f"Repaying {amount} DAI to Aave ...")
    repay_txn = lending_pool.repay(
        erc_token_address,
        amount_wei,
        1,
        account.address,
        {"from": account},
    )
    repay_txn.wait(1)
    print(f"... Done! {account.address} has repaid {amount} to Aave.\n")


def main():
    aave_borrow()
