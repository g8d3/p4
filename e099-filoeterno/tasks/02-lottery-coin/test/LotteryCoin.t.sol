// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;
import "../src/LotteryCoin.sol";
interface Vm { function warp(uint256 x) external; function prank(address a) external; function roll(uint256 n) external; }
contract LotteryCoinTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    LotteryCoin public coin;
    address alice = address(0xA11CE);
    address bob = address(0xB0B);
    function setUp() public {
        coin = new LotteryCoin();
        coin.transfer(alice, 5000 * 10**18);
    }
    function testFee() public {
        uint256 poolBefore = coin.balanceOf(address(coin));
        uint256 bobBefore = coin.balanceOf(bob);
        vm.prank(alice);
        coin.transfer(bob, 1000 * 10**18);
        require(coin.balanceOf(bob) == bobBefore + 990 * 10**18, "bob gets 990");
        require(coin.balanceOf(address(coin)) == poolBefore + 10 * 10**18, "pool gets 10");
    }
    function testOwnerExempt() public {
        address rec = address(0x0E11);
        uint256 poolBefore = coin.balanceOf(address(coin));
        coin.transfer(rec, 1000 * 10**18);
        require(coin.balanceOf(rec) == 990 * 10**18, "owner fee applies");
        require(coin.balanceOf(address(coin)) == poolBefore + 10 * 10**18, "owner pool fee");
    }
    function testEnterAndDraw() public {
        coin.transfer(alice, 5000 * 10**18);
        require(coin.balanceOf(alice) >= 1000 * 10**18, "alice funded");
        vm.prank(alice);
        coin.enter();
        require(coin.getEntryCount(0) == 1, "entered");
        vm.warp(coin.startTime() + 7 days + 1);
        coin.drawWinner(0);
        vm.roll(block.number + 6);
        coin.finalizeWinner(0);
        require(coin.roundWinner(0) == alice, "alice winner");
        uint256 prize = coin.roundPrize(0);
        require(prize > 0, "prize set");
        uint256 balBefore = coin.balanceOf(alice);
        vm.prank(alice);
        coin.claimPrize(0);
        require(coin.balanceOf(alice) == balBefore + prize, "prize paid");
        vm.prank(alice);
        try coin.claimPrize(0) {
            require(false, "second claim should revert");
        } catch {}
    }
    function testDoubleEnterFails() public {
        vm.prank(alice);
        coin.enter();
        vm.prank(alice);
        try coin.enter() {
            require(false, "double enter should revert");
        } catch {}
    }
    function testEarlyDrawFails() public {
        vm.prank(alice);
        coin.enter();
        try coin.drawWinner(0) {
            require(false, "early draw should revert");
        } catch {}
    }
}
