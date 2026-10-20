// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

interface Vm { function warp(uint256 x) external; function prank(address a) external; }

import "../src/TipJarCoin.sol";

contract TipJarCoinTest {
Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
TipJarCoin public coin;
address public treasury = address(0xBEEF);
address public alice = address(0xA11cE);
address public bob = address(0xB0B);
address public carol = address(0xCA201);
function setUp() public {
coin = new TipJarCoin(treasury);
coin.transfer(treasury, 200000000 ether);
coin.transfer(alice, 100000 ether);
}
function testFee() public {
uint256 tBefore = coin.balanceOf(treasury);
vm.prank(alice);
coin.transfer(bob, 1000 ether);
require(coin.balanceOf(bob) == 990 ether, "bob gets 990");
require(coin.balanceOf(treasury) == tBefore + 10 ether, "treasury gets 10");
}
function testOwnerExempt() public {
uint256 tBefore = coin.balanceOf(treasury);
coin.transfer(bob, 1000 ether);
require(coin.balanceOf(bob) == 1000 ether, "bob gets 1000");
require(coin.balanceOf(treasury) == tBefore, "treasury unchanged");
}
function testGrantFlow() public {
uint256 twenty = coin.totalSupply() / 5;
uint256 ab = coin.balanceOf(alice);
if (ab < twenty) { coin.transfer(alice, twenty - ab); }
uint256 tBefore = coin.balanceOf(treasury);
uint256 cBefore = coin.balanceOf(carol);
require(tBefore >= 500 ether, "treasury funded");
vm.prank(alice);
uint256 id = coin.proposeGrant(carol, 500 ether, "grant");
vm.prank(alice);
coin.vote(id, true);
vm.warp(block.timestamp + 3 days + 1);
coin.executeGrant(id);
require(coin.balanceOf(carol) == cBefore + 500 ether, "carol up 500");
require(coin.balanceOf(treasury) == tBefore - 500 ether, "treasury down");
}
function testQuorumFails() public {
address small = address(0x510A11);
uint256 amt = coin.totalSupply() * 2 / 1000;
coin.transfer(small, amt);
vm.prank(small);
uint256 id = coin.proposeGrant(carol, 500 ether, "small");
vm.prank(small);
coin.vote(id, true);
vm.warp(block.timestamp + 3 days + 1);
try coin.executeGrant(id) { require(false, "should revert"); } catch {}
}
function testDoubleVoteFails() public {
uint256 need = coin.totalSupply() * 2 / 1000;
uint256 ab = coin.balanceOf(alice);
if (ab < need) { coin.transfer(alice, need - ab); }
vm.prank(alice);
uint256 id = coin.proposeGrant(carol, 500 ether, "double");
vm.prank(alice);
coin.vote(id, true);
vm.prank(alice);
try coin.vote(id, true) { require(false, "should revert"); } catch {}
}
}
