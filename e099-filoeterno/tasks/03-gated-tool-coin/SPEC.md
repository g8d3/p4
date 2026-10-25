# SPEC — 03-gated-tool-coin

contract_file: GateToolCoin.sol
contract_name: GateToolCoin
src_path: src/GateToolCoin.sol
test_path: test/GateToolCoin.t.sol
solc: 0.8.26
probe_pattern: FEE_BPS = 50
probe_replacement: FEE_BPS = 5000

## CONTRACT

Mission: Create self-contained `src/GateToolCoin.sol` with `pragma solidity 0.8.26;`, no imports. Implement ERC-20 + gated on-chain service.

Token config:
- `name = "Gate Tool Coin"`, `symbol = "GTC"`, `decimals = 18`.
- `uint256 public totalSupply`, `address public owner`, `address public treasury`.
- `mapping(address => uint256) public balanceOf`, `mapping(address => mapping(address => uint256)) public allowance`.
- Constants: `uint256 public constant FEE_BPS = 50;` (0.5% / 10000), `uint256 public constant MIN_HOLDING = 5000 * 1e18;`, `uint256 public constant BOUNTY = 50 * 1e18;`, `uint256 public constant MAX_OPEN = 3;`.
- `constructor(address _treasury)`: require `_treasury != address(0)`, set `owner = msg.sender`, `treasury = _treasury`, mint `1_000_000 * 1e18` to `owner`. Emit `Transfer(address(0), owner, 1_000_000 * 1e18)`.

ERC-20 standard:
- `event Transfer(address indexed from, address indexed to, uint256 value);`
- `event Approval(address indexed owner, address indexed spender, uint256 value);`
- `function approve(address spender, uint256 amount) external returns (bool)`: set allowance, emit Approval, return true.
- `function transfer(address to, uint256 amount) external returns (bool)`: call internal `_transfer(msg.sender, to, amount)`.
- `function transferFrom(address from, address to, uint256 amount) external returns (bool)`: require `allowance[from][msg.sender] >= amount`, decrement allowance, call `_transfer(from, to, amount)`.
- Fee split `_transfer`: require `from != address(0)`, `to != address(0)`, `balanceOf[from] >= amount`. Compute `fee = amount * FEE_BPS / 10000`, `net = amount - fee`. Update: `balanceOf[from] -= amount; balanceOf[to] += net; balanceOf[treasury] += fee;`. Emit `Transfer(from, treasury, fee)` if `fee > 0` and `Transfer(from, to, net)`. If `from == treasury` or `to == treasury` still apply same split (no exemption) except mint. Keep `totalSupply` unchanged.

Gated service:
- `struct Task { uint256 id; address submitter; string description; bool completed; bool claimed; }`
- `uint256 public taskCount; mapping(uint256 => Task) public tasks; mapping(address => uint256) public openCount;`
- Events: `event TaskSubmitted(uint256 indexed id, address indexed submitter, string description);` `event TaskCompleted(uint256 indexed id);` `event TaskClaimed(uint256 indexed id, address indexed claimer, uint256 bounty);`
- `function submitTask(string calldata description) external returns (uint256)`: require `balanceOf[msg.sender] >= MIN_HOLDING` else revert `NotHolder()`, require `bytes(description).length > 0`, require `openCount[msg.sender] < MAX_OPEN` else revert `TooManyOpen()`. Increment `taskCount`, store Task, increment `openCount[msg.sender]`, emit TaskSubmitted, return id.
- `function completeTask(uint256 taskId) external`: require `msg.sender == owner` else revert `NotOwner()`, require `taskId > 0 && taskId <= taskCount`, require `!tasks[taskId].completed` else revert `AlreadyDone()`. Set `completed = true`, decrement `openCount[submitter]`, emit TaskCompleted.
- `function claimTask(uint256 taskId) external`: require `tasks[taskId].submitter == msg.sender` else revert `NotSubmitter()`, require `tasks[taskId].completed` else revert `NotCompleted()`, require `!tasks[taskId].claimed` else revert `AlreadyClaimed()`, require `balanceOf[msg.sender] >= MIN_HOLDING` else revert `NotHolder()` (must still hold at claim). Pay fixed `BOUNTY` from `treasury`: require `balanceOf[treasury] >= BOUNTY` else revert `TreasuryEmpty()`, require `allowance[treasury][address(this)] >= BOUNTY` else revert `TreasuryNoAllowance()`. Do `allowance[treasury][address(this)] -= BOUNTY; balanceOf[treasury] -= BOUNTY; balanceOf[msg.sender] += BOUNTY;` Emit `Transfer(treasury, msg.sender, BOUNTY)` + `TaskClaimed`. Set `claimed = true`. No fee on bounty payout.
- Owner funds treasury separately: owner does plain `transfer(treasury, amount)` (incurs fee, account for it) to provide bounty liquidity, then treasury `approve(contract, amount)` so contract can pull bounties. Contract holds no special fund function.

## TESTS

Mission: Create self-contained `test/GateToolCoin.t.sol` with `pragma solidity 0.8.26;`, no imports except `import "../src/GateToolCoin.sol";`, no forge-std, never redefine contract. Define minimal cheatcode interface and use red-first probe pattern:

```solidity
interface Vm { function prank(address) external; function startPrank(address) external; function stopPrank() external; function roll(uint256) external; function warp(uint256) external; function expectRevert(bytes calldata) external; }
Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
```

Follow red-first: write failing probe on fee math first, then implement/fix to green.

Setup: deploy with `treasury = address(0x7777)`, owner is test contract. Fund holder `alice = address(0xA11CE)` with e.g. `20000 * 1e18` via transfer, fund `treasury` with e.g. `1000 * 1e18` via transfer from owner, then `vm.prank(treasury)` approve contract for bounties.

5 tests:
1. `test_FeeSplit`: red probe — transfer `10000 * 1e18` owner->alice, assert `balanceOf[treasury]` increased by `50 * 1e18` (0.5%), `balanceOf[alice]` increased by `9950 * 1e18`. Compute exact `fee = amount * 50 / 10000`.
2. `test_GateBlocksNonHolderSubmit`: `bob = address(0xB0B)` with 0 or < MIN_HOLDING tries `submitTask("x")` via `vm.prank(bob)` must revert. Use `vm.expectRevert` or try/catch. Also verify holder with >=5000 succeeds.
3. `test_FullFlowSubmitCompleteClaim`: alice (holder) `submitTask`, assert id=1, owner `completeTask(1)`, alice `claimTask(1)` via pranks, assert alice gained `BOUNTY (50 * 1e18)`, task `claimed == true`. Second `claimTask(1)` must fail (double-claim reverts).
4. `test_TreasuryAccounting`: record treasury balance after funding + fees, after one claim assert `treasuryAfter = treasuryBefore - BOUNTY`, fees from transfers accumulated correctly, treasury remains solvent for next bounty.
5. `test_EdgeEarlyDuplicate`: claim before complete reverts, complete by non-owner reverts, submit 4th open task reverts (max 3 anti-spam), complete twice reverts, claim by non-submitter reverts, claim after dumping tokens below MIN_HOLDING reverts.
