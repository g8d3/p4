// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;
contract TipJarCoin {
string public name = "TipJar";
string public symbol = "TIPJAR";
uint8 public decimals = 18;
uint256 public totalSupply;
address public owner;
address public treasury;
mapping(address => uint256) public balanceOf;
mapping(address => mapping(address => uint256)) public allowance;
struct Proposal {address proposer; address recipient; uint256 amount; string description; uint256 yesVotes; uint256 noVotes; uint256 deadline; bool executed; uint256 snapshotBlock; uint256 proposerBal; uint256 snapshotSupply;}
uint256 public proposalCount;
mapping(uint256 => Proposal) public proposals;
mapping(uint256 => mapping(address => bool)) public hasVoted;
bool private _locked;
mapping(address => uint256) public firstSeenBlock;
uint256 private _deployBlock;
event Transfer(address indexed from, address indexed to, uint256 value);
event Approval(address indexed owner_, address indexed spender, uint256 value);
event FeeCollected(address indexed from, address indexed treasury, uint256 fee);
event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
event GrantProposed(uint256 indexed id, address indexed proposer, address indexed recipient, uint256 amount, string description, uint256 deadline);
event Voted(uint256 indexed id, address indexed voter, bool support, uint256 weight);
event GrantExecuted(uint256 indexed id, address indexed recipient, uint256 amount);
modifier onlyOwner() {require(msg.sender == owner, "not owner"); _;}
modifier nonReentrant() {require(!_locked, "reentrant"); _locked = true; _; _locked = false;}
constructor(address _treasury) {require(_treasury != address(0), "treasury zero"); owner = msg.sender; treasury = _treasury; totalSupply = 1000000000 * 10 ** 18; balanceOf[msg.sender] = totalSupply; emit Transfer(address(0), msg.sender, totalSupply); _deployBlock = block.number;}
function transferOwnership(address newOwner) external onlyOwner {require(newOwner != address(0), "zero owner"); address old = owner; owner = newOwner; emit OwnershipTransferred(old, newOwner);}
function setTreasury(address newTreasury) external onlyOwner {require(newTreasury != address(0), "zero treasury"); address old = treasury; treasury = newTreasury; emit TreasuryUpdated(old, newTreasury);}
function approve(address spender, uint256 value) external returns (bool) {require(spender != address(0), "zero spender"); allowance[msg.sender][spender] = value; emit Approval(msg.sender, spender, value); return true;}
function transfer(address to, uint256 amount) external returns (bool) {_transfer(msg.sender, to, amount); return true;}
function transferFrom(address from, address to, uint256 amount) external returns (bool) {uint256 allowed = allowance[from][msg.sender]; require(allowed >= amount, "allowance low"); allowance[from][msg.sender] = allowed - amount; _transfer(from, to, amount); return true;}
function _transfer(address from, address to, uint256 amount) internal {require(from != address(0), "zero from"); require(to != address(0), "zero to"); require(amount > 0, "zero amount"); require(balanceOf[from] >= amount, "balance low"); require(treasury != address(0), "no treasury"); if (balanceOf[to] == 0 && firstSeenBlock[to] == 0 && block.number != _deployBlock) {firstSeenBlock[to] = block.number;} if (balanceOf[treasury] == 0 && firstSeenBlock[treasury] == 0 && block.number != _deployBlock && treasury != to) {firstSeenBlock[treasury] = block.number;} if (from == owner || to == treasury) {balanceOf[from] -= amount; balanceOf[to] += amount; emit Transfer(from, to, amount);} else {uint256 fee = amount / 100; uint256 net = amount - fee; balanceOf[from] -= amount; balanceOf[to] += net; emit Transfer(from, to, net); if (fee > 0) {balanceOf[treasury] += fee; emit Transfer(from, treasury, fee); emit FeeCollected(from, treasury, fee);}}}
function proposeGrant(address recipient, uint256 amount, string calldata description) external returns (uint256) {require(recipient != address(0), "zero recipient"); require(amount > 0, "zero amount"); require(balanceOf[msg.sender] * 1000 >= totalSupply, "need 0.1 pct"); uint256 id = proposalCount++; Proposal storage p = proposals[id]; p.proposer = msg.sender; p.recipient = recipient; p.amount = amount; p.description = description; p.deadline = block.timestamp + 3 days; p.snapshotBlock = block.number; p.proposerBal = balanceOf[msg.sender]; p.snapshotSupply = totalSupply; emit GrantProposed(id, msg.sender, recipient, amount, description, p.deadline); return id;}
function vote(uint256 proposalId, bool support) external {require(proposalId < proposalCount, "no proposal"); Proposal storage p = proposals[proposalId]; require(block.timestamp <= p.deadline, "voting ended"); require(!p.executed, "executed"); require(!hasVoted[proposalId][msg.sender], "already voted"); uint256 weight; if (msg.sender == p.proposer) {uint256 cur = balanceOf[msg.sender]; uint256 snap = p.proposerBal; weight = cur < snap ? cur : snap;} else {require(firstSeenBlock[msg.sender] < p.snapshotBlock, "flash voter"); weight = balanceOf[msg.sender];} require(weight > 0, "no weight"); hasVoted[proposalId][msg.sender] = true; if (support) {p.yesVotes += weight;} else {p.noVotes += weight;} emit Voted(proposalId, msg.sender, support, weight);}
function executeGrant(uint256 proposalId) external nonReentrant {require(proposalId < proposalCount, "no proposal"); Proposal storage p = proposals[proposalId]; require(!p.executed, "already executed"); require(block.timestamp >= p.deadline, "not ended"); require(p.yesVotes > p.noVotes, "yes not gt no"); require(p.yesVotes * 10 >= p.snapshotSupply, "quorum 10pct"); require(balanceOf[treasury] >= p.amount, "treasury low"); require(p.recipient != address(0), "zero recipient"); require(p.amount * 20 <= balanceOf[treasury], "grant >5pct"); p.executed = true; if (balanceOf[p.recipient] == 0 && firstSeenBlock[p.recipient] == 0) {firstSeenBlock[p.recipient] = block.number;} balanceOf[treasury] -= p.amount; balanceOf[p.recipient] += p.amount; emit Transfer(treasury, p.recipient, p.amount); emit GrantExecuted(proposalId, p.recipient, p.amount);}
// MEDIUM: owner is fee-exempt and can change treasury, centralization trust remains.
// MEDIUM: 1pct fee has no slippage guard and quorum counts treasury balance, no min voting period.
}
