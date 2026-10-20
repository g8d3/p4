# 02-lottery-coin
contract_file: LotteryCoin.sol
contract_name: LotteryCoin
probe_pattern: amount / 100
probe_replacement: amount / 50
## CONTRACT
Write ONE self-contained Solidity file (solc 0.8.26, NO imports, no OpenZeppelin).
Contract LotteryCoin, ERC-20 from scratch:
- name Lottery, symbol LOTTO, 18 decimals, 1_000_000 tokens minted to deployer.
- 1% fee on every transfer (taken from amount: recipient gets 99%, prize pool = contract balance grows by 1%). No fee on mint. Owner = deployer, can transferOwnership.
- Weekly lottery rounds: ROUND = 7 days. During a round, any holder with >= 1000 tokens can enter ONCE per round (enter() records entry, entry count per round). After round deadline anyone can drawWinner(roundId): winner = entries[uint256(blockhash of a past block) % entries.length] (note in code comments that blockhash randomness is manipulable and prizes must stay small). Prize = 90% of fees collected that round (track per-round pool); 10% stays as rollover. Winner claims via claimPrize(roundId) once; reentrancy guard on claim.
- Events for fee, entry, winner, claim. Zero-address checks.
## TESTS
Write a Foundry test file WITHOUT forge-std (no libs): plain contract with `function testX()` using `require(cond, "msg")`. Minimal Vm interface for warp/prank:
interface Vm { function warp(uint256 x) external; function prank(address a) external; }
`Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));`
Import the contract under test with `import "../src/LotteryCoin.sol";` — NEVER redefine the contract in the test file.
Tests: testFee (non-owner transfer 1000 -> recipient 990, pool 10); testOwnerExempt; testEnterAndDraw (fund alice 5000, enter, warp past 7 days + 1, draw, claim, alice balance up by prize, second claim reverts via try/catch); testDoubleEnterFails (enter twice, second reverts); testEarlyDrawFails (draw before deadline reverts).
Constructor: constructor(address _treasury) is NOT needed here — no treasury; constructor() mints to deployer. setUp deploys and funds alice via owner-exempt transfer.
