// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;
import "../src/GateToolCoin.sol";
interface Vm { function prank(address) external; function startPrank(address) external; function stopPrank() external; function roll(uint256) external; function warp(uint256) external; function expectRevert(bytes calldata) external; }
Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
contract GateToolCoinTest {
 GateToolCoin public gate;
 address public treasury = address(0x7777);
 address public alice = address(0xA11CE);
 address public bob = address(0xB0B);
 function setUp() public {
  gate = new GateToolCoin(treasury);
  gate.transfer(alice, 20000 * 1e18);
  gate.transfer(treasury, 1000 * 1e18);
  vm.prank(treasury);
  gate.approve(address(gate), type(uint256).max);
 }
 function test_FeeSplit() public {
  uint256 amount = 10000 * 1e18;
  uint256 expectedFee = amount * 50 / 10000;
  require(expectedFee == 50 * 1e18, "fee math");
  uint256 tBefore = gate.balanceOf(treasury);
  uint256 aBefore = gate.balanceOf(alice);
  gate.transfer(alice, amount);
  uint256 tAfter = gate.balanceOf(treasury);
  uint256 aAfter = gate.balanceOf(alice);
  require(tAfter - tBefore == expectedFee, "treasury fee");
  require(aAfter - aBefore == 9950 * 1e18, "alice net");
  require(aAfter - aBefore == amount - expectedFee, "net math");
 }
 function test_GateBlocksNonHolderSubmit() public {
  vm.expectRevert(abi.encodeWithSignature("NotHolder()"));
  vm.prank(bob);
  gate.submitTask("x");
  gate.transfer(bob, 1000 * 1e18);
  vm.expectRevert(abi.encodeWithSignature("NotHolder()"));
  vm.prank(bob);
  gate.submitTask("y");
  vm.prank(alice);
  uint256 id = gate.submitTask("holder ok");
  require(id == 1, "holder id");
 }
 function test_FullFlowSubmitCompleteClaim() public {
  vm.prank(alice);
  uint256 id = gate.submitTask("build tool");
  require(id == 1, "id 1");
  gate.completeTask(1);
  uint256 aBefore = gate.balanceOf(alice);
  vm.prank(alice);
  gate.claimTask(1);
  uint256 aAfter = gate.balanceOf(alice);
  require(aAfter - aBefore == 50 * 1e18, "bounty");
  require(aAfter - aBefore == gate.BOUNTY(), "bounty const");
  (uint256 _id, address _sub, string memory _d, bool _comp, bool _claimed) = gate.tasks(1);
  require(_claimed, "claimed true");
  require(_comp, "completed true");
  require(_sub == alice, "submitter");
  require(_id == 1, "task id");
  require(bytes(_d).length > 0, "desc");
  vm.expectRevert(abi.encodeWithSignature("AlreadyClaimed()"));
  vm.prank(alice);
  gate.claimTask(1);
 }
 function test_TreasuryAccounting() public {
  uint256 t0 = gate.balanceOf(treasury);
  uint256 amount = 10000 * 1e18;
  uint256 fee = amount * 50 / 10000;
  gate.transfer(alice, amount);
  uint256 tAfterFee = gate.balanceOf(treasury);
  require(tAfterFee - t0 == fee, "fee accum");
  vm.prank(alice);
  gate.submitTask("acct task");
  gate.completeTask(1);
  uint256 tBeforeClaim = gate.balanceOf(treasury);
  vm.prank(alice);
  gate.claimTask(1);
  uint256 tAfterClaim = gate.balanceOf(treasury);
  require(tBeforeClaim - tAfterClaim == gate.BOUNTY(), "treasury bounty");
  require(tAfterClaim == tAfterFee - 50 * 1e18, "accounting");
  require(tAfterClaim >= gate.BOUNTY(), "solvent next");
 }
 function test_EdgeEarlyDuplicate() public {
  vm.prank(alice);
  uint256 id1 = gate.submitTask("t1");
  require(id1 == 1, "id1");
  vm.expectRevert(abi.encodeWithSignature("NotCompleted()"));
  vm.prank(alice);
  gate.claimTask(id1);
  vm.expectRevert(abi.encodeWithSignature("NotOwner()"));
  vm.prank(bob);
  gate.completeTask(id1);
  vm.prank(alice);
  gate.submitTask("t2");
  vm.prank(alice);
  gate.submitTask("t3");
  vm.expectRevert(abi.encodeWithSignature("TooManyOpen()"));
  vm.prank(alice);
  gate.submitTask("t4");
  gate.completeTask(id1);
  vm.expectRevert(abi.encodeWithSignature("AlreadyDone()"));
  gate.completeTask(id1);
  vm.expectRevert(abi.encodeWithSignature("NotSubmitter()"));
  vm.prank(bob);
  gate.claimTask(id1);
  vm.prank(alice);
  gate.transfer(bob, 15000 * 1e18);
  require(gate.balanceOf(alice) < gate.MIN_HOLDING(), "dumped");
  vm.expectRevert(abi.encodeWithSignature("NotHolder()"));
  vm.prank(alice);
  gate.claimTask(id1);
 }
}
