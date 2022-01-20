from brownie import config, network, interface
from scripts.helpful_scripts import get_account
from web3 import Web3


def get_weth(amount=0.1):
    """Mints WETH by depositing ETH"""
    # we need to access the WETH contract
    account = get_account()

    weth = interface.IWeth(config["networks"][network.show_active()]["weth_token"])

    print(f"Depositing {amount} ETH for WETH ...")
    txn = weth.deposit({"from": account, "value": Web3.toWei(amount, "ether")})
    txn.wait(1)
    print(f"... Done! Received {amount} WETH.\n")
    return txn


def main():
    get_weth()
