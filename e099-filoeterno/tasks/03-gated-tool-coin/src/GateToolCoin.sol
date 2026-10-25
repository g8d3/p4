// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;
contract GateToolCoin {
 string public name = "Gate Tool Coin";
 string public symbol = "GTC";
 uint8 public decimals = 18;
 uint256 public totalSupply;
 address public owner;
 address public treasury;
 mapping(address => uint256) public balanceOf;
 mapping(address => mapping(address => uint256)) public allowance;
 uint256 public constant FEE_BPS = 50;
 uint256 public constant MIN_HOLDING = 5000 * 1e18;
 uint256 public constant BOUNTY = 50 * 1e18;
 uint256 public constant MAX_OPEN = 3;
 uint256 public maxDescLen = 2000;
 uint256 public taskCount;
 mapping(uint256 => Task) public tasks;
 mapping(address => uint256) public openCount;
 struct Task { uint256 id; address submitter; string description; bool completed; bool claimed; }
 error NotHolder();
 error TooManyOpen();
 error NotOwner();
 error AlreadyDone();
 error NotSubmitter();
 error NotCompleted();
 error AlreadyClaimed();
 error TreasuryEmpty();
 error TreasuryNoAllowance();
 error Paused();
 error DescTooLong();
 error SelfDealing();
 error NotApproved();
 error CapExceeded();
 error Expired();
 error NotExpired();
 error Timelocked();
 error ZeroAddress();
 error NotReviewer();
 error NotTreasury();
 error NoPending();
 error InsufficientFunding();
 event Transfer(address indexed from, address indexed to, uint256 value);
 event Approval(address indexed owner, address indexed spender, uint256 value);
 event TaskSubmitted(uint256 indexed id, address indexed submitter, string description);
 event TaskCompleted(uint256 indexed id);
 event TaskClaimed(uint256 indexed id, address indexed claimer, uint256 bounty);
 event TaskCancelled(uint256 indexed id);
 event TaskCancelReason(uint256 indexed id, string reason);
 event PoolFunded(address indexed from, uint256 amount);
 event BountyEscrowed(uint256 indexed id, uint256 amount);
 event ReviewerUpdated(address indexed reviewer, bool allowed);
 event Staked(address indexed user, uint256 amount);
 event Unstaked(address indexed user, uint256 amount);
 event SubmitFeeUpdated(uint256 fee);
 event FeesWithdrawn(address indexed to, uint256 amount);
 mapping(address => bool) public isReviewer;
 mapping(address => uint256) public staked;
 mapping(address => uint256) public reputation;
 mapping(address => uint256) public feesPaid;
 mapping(address => uint256) public stakeUnlockAt;
 mapping(uint256 => uint256) public escrowed;
 mapping(uint256 => uint256) public completedAt;
 mapping(uint256 => uint256) public submittedAt;
 uint256 public totalEscrowed;
 uint256 public maxTotalEscrow;
 uint256 public totalStaked;
 uint256 public submitFee;
 uint256 public lastSubmitBlock;
 uint256 public submitsThisBlock;
 uint256 public constant MAX_SUBMITS_PER_BLOCK = 20;
 uint256 public constant CLAIM_WINDOW = 90 days;
 uint256 public constant TASK_EXPIRY = 30 days;
 uint256 public constant STAKE_LOCK = 1 days;
 uint256 public constant REP_EPOCH = 30 days;
 uint256 public constant MAX_REP_PER_EPOCH = 5;
 mapping(address => uint256) public repEpoch;
 mapping(address => uint256) public repInEpoch;
 uint256 public poolReserve;
 uint256 public feeReserve;
 mapping(uint256 => bool) public treasuryApproved;
 mapping(uint256 => uint256) public treasuryApprovalExpiry;
 mapping(uint256 => address) public completedBy;
 mapping(uint256 => string) public completionReason;
 mapping(uint256 => bool) public disputed;
 mapping(uint256 => string) public disputeReason;
 mapping(address => uint256) public reviewerEscrowed;
 uint256 public maxPerReviewer;
 address public guardian;
 uint256 public constant GOV_DELAY = 1 days;
 mapping(address => uint256) public reviewerProposedAt;
 mapping(address => bool) public reviewerProposedValue;
 mapping(address => bool) public reviewerProposedExists;
 uint256 public pendingMaxEscrow;
 uint256 public maxEscrowProposedAt;
 bool public maxEscrowPending;
 uint256 public nextPayoutId = 1;
 uint256 public withdrawDelay;
 uint256 public pendingFeeWithdraw;
 uint256 public feeWithdrawReadyAt;
 bool public treasuryHalted;
 mapping(address => uint256) public activeDisputes;
 uint256 public constant CLEANUP_GRACE = 7 days;
 uint256 public constant DISPUTE_CHALLENGE_WINDOW = 2 days;
 mapping(uint256 => uint256) public disputedAt;
 mapping(address => uint256) public reviewerLastComplete;
 uint256 public reviewerCooldown;
 uint256 private _locked;
 modifier nonReentrant() { if (_locked == 1) revert Paused(); _locked = 1; _; _locked = 0; }
 event TreasuryTaskApproved(uint256 indexed id);
 event TaskCompletedWithReason(uint256 indexed id, address indexed reviewer, string reason);
 event TaskDisputed(uint256 indexed id, string reason);
 event DisputeResolved(uint256 indexed id, bool upheld);
 event ReviewerProposed(address indexed reviewer, bool allowed);
 event ReviewerConfirmed(address indexed reviewer, bool allowed);
 event MaxEscrowProposed(uint256 cap);
 event MaxEscrowConfirmed(uint256 cap);
 event GuardianUpdated(address indexed guardian);
 event FeeWithdrawRequested(uint256 amount, uint256 readyAt);
 event FeeWithdrawExecuted(address indexed to, uint256 amount);
 event StakeSlashed(address indexed reviewer, uint256 amount);
 event TreasuryHalted(bool halted);
 event StaleEscrowCleaned(uint256 indexed id);
 address public pendingGuardian;
 uint256 public guardianProposedAt;
 bool public guardianPending;
 uint256 public disputeBond;
 uint256 public constant DISPUTE_EXPIRY = 30 days;
 event GuardianProposed(address indexed guardian);
 event GuardianConfirmed(address indexed guardian);
 event DisputeBondUpdated(uint256 bond);
 event DisputeExpired(uint256 indexed id);
 mapping(uint256 => address) public disputeBy;
 mapping(uint256 => uint256) public disputeBondPaid;
 mapping(uint256 => uint256) public disputeCount;
 mapping(uint256 => uint256) public lastDisputeAt;
 mapping(address => uint256) public lastDisputeTime;
 uint256 public constant MAX_DISPUTES_PER_TASK = 3;
 uint256 public constant DISPUTE_COOLDOWN = 1 days;
 uint256 public pendingPoolWithdraw;
 uint256 public poolWithdrawReadyAt;
 event PoolWithdrawRequested(uint256 amount, uint256 readyAt);
 event PoolWithdrawExecuted(address indexed to, uint256 amount);
 uint256 public constant MAX_SUBMIT_FEE = 10 * 1e18;
 uint256 public constant MIN_DESC_LEN = 100;
 uint256 public constant MAX_DESC_LEN_CAP = 10000;
 uint256 public constant MAX_DISPUTE_BOND = 10 * 1e18;
 uint256 public constant MAX_PER_REVIEWER_CAP = 100000 * 1e18;
 uint256 public constant MAX_TREASURY_SPEND_PER_EPOCH = 500000 * 1e18;
 uint256 public constant TREASURY_EPOCH = 30 days;
 uint256 public treasurySpendEpoch;
 uint256 public treasurySpentInEpoch;
 uint256 public pendingSubmitFee;
 uint256 public submitFeeProposedAt;
 bool public submitFeePending;
 uint256 public pendingMaxDescLen;
 uint256 public maxDescLenProposedAt;
 bool public maxDescLenPending;
 uint256 public pendingMaxPerReviewer;
 uint256 public maxPerReviewerProposedAt;
 bool public maxPerReviewerPending;
 uint256 public pendingDisputeBond;
 uint256 public disputeBondProposedAt;
 bool public disputeBondPending;
 uint256 public pendingReviewerCooldown;
 uint256 public reviewerCooldownProposedAt;
 bool public reviewerCooldownPending;
 uint256 public pendingWithdrawDelay;
 uint256 public withdrawDelayProposedAt;
 bool public withdrawDelayPending;
 bool public haltPending;
 bool public haltPendingValue;
 address public haltProposer;
 uint256 public haltProposedAt;
 event SubmitFeeProposed(uint256 fee);
 event SubmitFeeConfirmed(uint256 fee);
 event MaxDescLenProposed(uint256 len);
 event MaxDescLenConfirmed(uint256 len);
 event MaxPerReviewerProposed(uint256 cap);
 event MaxPerReviewerConfirmed(uint256 cap);
 event DisputeBondProposed(uint256 bond);
 event DisputeBondConfirmed(uint256 bond);
 event ReviewerCooldownProposed(uint256 c);
 event ReviewerCooldownConfirmed(uint256 c);
 event WithdrawDelayProposed(uint256 d);
 event WithdrawDelayConfirmed(uint256 d);
 event TreasuryHaltProposed(bool halted, address indexed proposer);
 event DisputeBondSlashed(uint256 indexed id, address indexed disputer, uint256 amount);
 event DisputeBondRefunded(uint256 indexed id, address indexed disputer, uint256 amount);
 mapping(bytes32 => uint256) public reviewerSubmitterEpochCount;
 constructor(address _treasury) { require(_treasury != address(0)); owner = msg.sender; treasury = _treasury; totalSupply = 1000000 * 1e18; balanceOf[owner] = totalSupply; isReviewer[owner] = true; submitFee = 1 * 1e18; maxTotalEscrow = 500000 * 1e18; maxPerReviewer = 10000 * 1e18; disputeBond = 1 * 1e18; withdrawDelay = 1 days; emit Transfer(address(0), owner, totalSupply); }
 function setGuardian(address g) external { if (msg.sender != owner) revert NotOwner(); if (g == address(0)) revert ZeroAddress(); pendingGuardian = g; guardianProposedAt = block.timestamp; guardianPending = true; emit GuardianProposed(g); }
 function proposeGuardian(address g) external { if (msg.sender != owner) revert NotOwner(); pendingGuardian = g; guardianProposedAt = block.timestamp; guardianPending = true; emit GuardianProposed(g); }
 function confirmGuardian() external { if (msg.sender != owner && msg.sender != guardian) revert NotOwner(); if (!guardianPending) revert NoPending(); if (block.timestamp < guardianProposedAt + GOV_DELAY) revert Timelocked(); guardian = pendingGuardian; guardianPending = false; delete pendingGuardian; delete guardianProposedAt; emit GuardianUpdated(guardian); emit GuardianConfirmed(guardian); }
 function setReviewer(address r, bool v) external { if (msg.sender != owner) revert NotOwner(); if (r == address(0)) revert ZeroAddress(); reviewerProposedValue[r]=v; reviewerProposedAt[r]=block.timestamp; reviewerProposedExists[r]=true; emit ReviewerProposed(r,v); }
 function proposeReviewer(address r, bool v) external { if (msg.sender != owner) revert NotOwner(); if (r==address(0)) revert ZeroAddress(); reviewerProposedValue[r]=v; reviewerProposedAt[r]=block.timestamp; reviewerProposedExists[r]=true; emit ReviewerProposed(r,v); }
 function confirmReviewer(address r) external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!reviewerProposedExists[r]) revert NoPending(); if (block.timestamp < reviewerProposedAt[r]+GOV_DELAY) revert Timelocked(); isReviewer[r]=reviewerProposedValue[r]; delete reviewerProposedExists[r]; delete reviewerProposedAt[r]; emit ReviewerUpdated(r, isReviewer[r]); emit ReviewerConfirmed(r, isReviewer[r]); }
 function setSubmitFee(uint256 f) external { if (msg.sender != owner) revert NotOwner(); if (f > MAX_SUBMIT_FEE) revert CapExceeded(); pendingSubmitFee = f; submitFeeProposedAt = block.timestamp; submitFeePending = true; emit SubmitFeeProposed(f); }
 function confirmSubmitFee() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!submitFeePending) revert NoPending(); if (block.timestamp < submitFeeProposedAt + GOV_DELAY) revert Timelocked(); if (pendingSubmitFee > MAX_SUBMIT_FEE) revert CapExceeded(); submitFee = pendingSubmitFee; submitFeePending = false; emit SubmitFeeUpdated(submitFee); emit SubmitFeeConfirmed(submitFee); }
 function setMaxDescLen(uint256 l) external { if (msg.sender != owner) revert NotOwner(); if (l < MIN_DESC_LEN || l > MAX_DESC_LEN_CAP) revert CapExceeded(); pendingMaxDescLen = l; maxDescLenProposedAt = block.timestamp; maxDescLenPending = true; emit MaxDescLenProposed(l); }
 function confirmMaxDescLen() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!maxDescLenPending) revert NoPending(); if (block.timestamp < maxDescLenProposedAt+GOV_DELAY) revert Timelocked(); if (pendingMaxDescLen < MIN_DESC_LEN || pendingMaxDescLen > MAX_DESC_LEN_CAP) revert CapExceeded(); maxDescLen = pendingMaxDescLen; maxDescLenPending = false; emit MaxDescLenConfirmed(maxDescLen); }
 function setMaxTotalEscrow(uint256 c) external { if (msg.sender != owner) revert NotOwner(); if (c < totalEscrowed) revert CapExceeded(); if (c < poolReserve) revert CapExceeded(); pendingMaxEscrow=c; maxEscrowProposedAt=block.timestamp; maxEscrowPending=true; emit MaxEscrowProposed(c); }
 function proposeMaxTotalEscrow(uint256 c) external { if (msg.sender!=owner) revert NotOwner(); if (c < totalEscrowed) revert CapExceeded(); pendingMaxEscrow=c; maxEscrowProposedAt=block.timestamp; maxEscrowPending=true; emit MaxEscrowProposed(c); }
 function confirmMaxTotalEscrow() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!maxEscrowPending) revert NoPending(); if (block.timestamp < maxEscrowProposedAt+GOV_DELAY) revert Timelocked(); if (pendingMaxEscrow < totalEscrowed) revert CapExceeded(); maxTotalEscrow=pendingMaxEscrow; maxEscrowPending=false; emit MaxEscrowConfirmed(maxTotalEscrow); }
 function setMaxPerReviewer(uint256 c) external { if (msg.sender!=owner) revert NotOwner(); if (c < BOUNTY || c > MAX_PER_REVIEWER_CAP) revert CapExceeded(); pendingMaxPerReviewer = c; maxPerReviewerProposedAt = block.timestamp; maxPerReviewerPending = true; emit MaxPerReviewerProposed(c); }
 function confirmMaxPerReviewer() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!maxPerReviewerPending) revert NoPending(); if (block.timestamp < maxPerReviewerProposedAt+GOV_DELAY) revert Timelocked(); if (pendingMaxPerReviewer < BOUNTY || pendingMaxPerReviewer > MAX_PER_REVIEWER_CAP) revert CapExceeded(); maxPerReviewer = pendingMaxPerReviewer; maxPerReviewerPending = false; emit MaxPerReviewerConfirmed(maxPerReviewer); }
 function setReviewerCooldown(uint256 c) external { if (msg.sender != owner) revert NotOwner(); if (c == 0) revert CapExceeded(); if (c > 7 days) revert CapExceeded(); pendingReviewerCooldown = c; reviewerCooldownProposedAt = block.timestamp; reviewerCooldownPending = true; emit ReviewerCooldownProposed(c); }
 function confirmReviewerCooldown() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!reviewerCooldownPending) revert NoPending(); if (block.timestamp < reviewerCooldownProposedAt+GOV_DELAY) revert Timelocked(); if (pendingReviewerCooldown == 0 || pendingReviewerCooldown > 7 days) revert CapExceeded(); reviewerCooldown = pendingReviewerCooldown; reviewerCooldownPending = false; emit ReviewerCooldownConfirmed(reviewerCooldown); }
 function setWithdrawDelay(uint256 d) external { if (msg.sender!=owner && msg.sender!=treasury && msg.sender!=guardian) revert NotOwner(); if (d>30 days) revert CapExceeded(); pendingWithdrawDelay = d; withdrawDelayProposedAt = block.timestamp; withdrawDelayPending = true; emit WithdrawDelayProposed(d); }
 function confirmWithdrawDelay() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!withdrawDelayPending) revert NoPending(); if (block.timestamp < withdrawDelayProposedAt+GOV_DELAY) revert Timelocked(); if (pendingWithdrawDelay > 30 days) revert CapExceeded(); withdrawDelay = pendingWithdrawDelay; withdrawDelayPending = false; emit WithdrawDelayConfirmed(withdrawDelay); }
 function setTreasuryHalted(bool v) external { if (guardian == address(0)) { if (msg.sender!=treasury) revert NotTreasury(); treasuryHalted = v; emit TreasuryHalted(v); return; } if (msg.sender!=treasury && msg.sender!=guardian) revert NotTreasury(); if (!haltPending) { haltPending = true; haltPendingValue = v; haltProposer = msg.sender; haltProposedAt = block.timestamp; emit TreasuryHaltProposed(v, msg.sender); return; } if (haltPendingValue != v) revert NoPending(); if (msg.sender == haltProposer) revert NotTreasury(); treasuryHalted = v; haltPending = false; delete haltProposer; delete haltProposedAt; emit TreasuryHalted(v); }
 function setDisputeBond(uint256 b) external { if (msg.sender != owner) revert NotOwner(); if (b > MAX_DISPUTE_BOND) revert CapExceeded(); pendingDisputeBond = b; disputeBondProposedAt = block.timestamp; disputeBondPending = true; emit DisputeBondProposed(b); }
 function confirmDisputeBond() external { if (msg.sender!=owner && msg.sender!=guardian) revert NotOwner(); if (!disputeBondPending) revert NoPending(); if (block.timestamp < disputeBondProposedAt+GOV_DELAY) revert Timelocked(); if (pendingDisputeBond > MAX_DISPUTE_BOND) revert CapExceeded(); disputeBond = pendingDisputeBond; disputeBondPending = false; emit DisputeBondUpdated(disputeBond); emit DisputeBondConfirmed(disputeBond); }
 function approveTask(uint256 taskId) external { if (msg.sender!=treasury) revert NotTreasury(); require(taskId>0 && taskId<=taskCount); treasuryApproved[taskId]=true; treasuryApprovalExpiry[taskId]=block.timestamp+TASK_EXPIRY; emit TreasuryTaskApproved(taskId); }
 function stake(uint256 amount) external { require(amount > 0); require(balanceOf[msg.sender] >= amount); balanceOf[msg.sender] -= amount; balanceOf[address(this)] += amount; staked[msg.sender] += amount; totalStaked += amount; stakeUnlockAt[msg.sender] = block.timestamp + STAKE_LOCK; emit Transfer(msg.sender, address(this), amount); emit Staked(msg.sender, amount); }
 function unstake(uint256 amount) external nonReentrant { if (block.timestamp < stakeUnlockAt[msg.sender]) revert Timelocked(); if (staked[msg.sender] < amount) revert NotHolder(); if (staked[msg.sender] - amount < reviewerEscrowed[msg.sender]) revert Paused(); staked[msg.sender] -= amount; totalStaked -= amount; balanceOf[address(this)] -= amount; balanceOf[msg.sender] += amount; emit Transfer(address(this), msg.sender, amount); emit Unstaked(msg.sender, amount); }
 function fundBountyPool(uint256 amount) external { if (msg.sender != treasury) revert NotTreasury(); if (amount == 0) revert NoPending(); if (amount > MAX_TREASURY_SPEND_PER_EPOCH) revert CapExceeded(); uint256 cur = block.timestamp / TREASURY_EPOCH; if (treasurySpendEpoch != cur) { treasurySpendEpoch = cur; treasurySpentInEpoch = 0; } if (treasurySpentInEpoch + amount > MAX_TREASURY_SPEND_PER_EPOCH) revert CapExceeded(); treasurySpentInEpoch += amount; if (balanceOf[treasury] < amount) revert TreasuryEmpty(); if (allowance[treasury][address(this)] < amount) revert TreasuryNoAllowance(); allowance[treasury][address(this)] -= amount; balanceOf[treasury] -= amount; balanceOf[address(this)] += amount; poolReserve += amount; emit Transfer(treasury, address(this), amount); emit PoolFunded(msg.sender, amount); }
 function approve(address spender, uint256 amount) external returns (bool) { allowance[msg.sender][spender] = amount; emit Approval(msg.sender, spender, amount); return true; }
 function transfer(address to, uint256 amount) external returns (bool) { _transfer(msg.sender, to, amount); return true; }
 function transferFrom(address from, address to, uint256 amount) external returns (bool) { require(allowance[from][msg.sender] >= amount); allowance[from][msg.sender] -= amount; _transfer(from, to, amount); return true; }
 function _transfer(address from, address to, uint256 amount) internal { require(from != address(0)); require(to != address(0)); require(balanceOf[from] >= amount); uint256 fee = amount * FEE_BPS / 10000; uint256 net = amount - fee; balanceOf[from] -= amount; balanceOf[to] += net; balanceOf[treasury] += fee; if (fee > 0) emit Transfer(from, treasury, fee); emit Transfer(from, to, net); }
 function _holding(address a) internal view returns (uint256) { return balanceOf[a] + staked[a]; }
 function _grantRep(address u) internal { uint256 cur = block.timestamp / REP_EPOCH; if (repEpoch[u] != cur) { repEpoch[u] = cur; repInEpoch[u] = 0; } if (repInEpoch[u] >= MAX_REP_PER_EPOCH) return; repInEpoch[u]++; reputation[u] += 1; }
 function submitTask(string calldata description) external returns (uint256) { if (msg.sender == owner || msg.sender == treasury) revert SelfDealing(); if (_holding(msg.sender) < MIN_HOLDING) revert NotHolder(); require(bytes(description).length > 0); if (bytes(description).length > maxDescLen) revert DescTooLong(); if (openCount[msg.sender] >= MAX_OPEN) revert TooManyOpen(); if (block.number == lastSubmitBlock) { if (submitsThisBlock >= MAX_SUBMITS_PER_BLOCK) revert CapExceeded(); submitsThisBlock++; } else { lastSubmitBlock = block.number; submitsThisBlock = 1; } if (submitFee > 0) { if (balanceOf[msg.sender] < submitFee) revert NotHolder(); balanceOf[msg.sender] -= submitFee; balanceOf[address(this)] += submitFee; feeReserve += submitFee; feesPaid[msg.sender] += submitFee; emit Transfer(msg.sender, address(this), submitFee); } taskCount++; uint256 id = taskCount; tasks[id] = Task({id: id, submitter: msg.sender, description: description, completed: false, claimed: false}); submittedAt[id] = block.timestamp; openCount[msg.sender]++; emit TaskSubmitted(id, msg.sender, description); return id; }
 function _fundAtCompletion() internal view { if (treasuryHalted) revert Paused(); if (poolReserve < totalEscrowed) revert CapExceeded(); if (poolReserve < totalEscrowed + BOUNTY) { if (balanceOf[treasury] < BOUNTY) revert InsufficientFunding(); if (allowance[treasury][address(this)] < BOUNTY) revert TreasuryNoAllowance(); } if (balanceOf[address(this)] + balanceOf[treasury] < BOUNTY) revert TreasuryEmpty(); }
 function _fundAtClaim(uint256 esc) internal view { if (treasuryHalted) revert Paused(); if (esc == 0) revert NoPending(); if (poolReserve < esc) revert InsufficientFunding(); if (poolReserve < totalEscrowed) revert CapExceeded(); if (balanceOf[address(this)] < esc) revert TreasuryEmpty(); }
 function _pullBounty(uint256 esc) internal view { if (treasuryHalted) revert Paused(); if (esc == 0) revert NoPending(); if (poolReserve < esc) revert InsufficientFunding(); if (poolReserve < totalEscrowed) revert CapExceeded(); if (balanceOf[address(this)] < esc) revert TreasuryEmpty(); }
 function _refundBond(uint256 taskId) internal { address disputer = disputeBy[taskId]; uint256 bpaid = disputeBondPaid[taskId]; if (disputer != address(0) && bpaid > 0) { if (feeReserve >= bpaid) feeReserve -= bpaid; else feeReserve = 0; balanceOf[address(this)] -= bpaid; balanceOf[disputer] += bpaid; emit Transfer(address(this), disputer, bpaid); emit DisputeBondRefunded(taskId, disputer, bpaid); } disputeBy[taskId]=address(0); disputeBondPaid[taskId]=0; }
 function _slashBond(uint256 taskId) internal { address disputer = disputeBy[taskId]; uint256 bpaid = disputeBondPaid[taskId]; if (disputer != address(0) && bpaid > 0) { if (feeReserve >= bpaid) feeReserve -= bpaid; else feeReserve = 0; balanceOf[address(this)] -= bpaid; balanceOf[treasury] += bpaid; emit Transfer(address(this), treasury, bpaid); emit DisputeBondSlashed(taskId, disputer, bpaid); } disputeBy[taskId]=address(0); disputeBondPaid[taskId]=0; }
 function _complete(uint256 taskId, string memory reason) internal { if (!isReviewer[msg.sender]) revert NotOwner(); require(taskId > 0 && taskId <= taskCount); if (treasuryHalted) revert Paused(); if (block.timestamp < reviewerLastComplete[msg.sender] + reviewerCooldown) revert Timelocked(); if (_holding(msg.sender) < MIN_HOLDING) revert NotHolder(); if (activeDisputes[msg.sender] > 0) revert Paused(); Task storage t = tasks[taskId]; if (t.completed || t.claimed) revert AlreadyDone(); if (t.submitter == owner || t.submitter == treasury) revert SelfDealing(); if (msg.sender == t.submitter) revert SelfDealing(); if (disputed[taskId]) revert Paused(); if (bytes(t.description).length == 0) revert NotCompleted(); if (block.timestamp > submittedAt[taskId] + TASK_EXPIRY) revert Expired(); if (_holding(t.submitter) < MIN_HOLDING) revert NotHolder(); if (totalEscrowed + BOUNTY > maxTotalEscrow) revert CapExceeded(); if (reviewerEscrowed[msg.sender] + BOUNTY > maxPerReviewer) revert CapExceeded(); uint256 _epoch = block.timestamp / REP_EPOCH; bytes32 _pairKey = keccak256(abi.encodePacked(msg.sender, t.submitter, _epoch)); if (reviewerSubmitterEpochCount[_pairKey] >= MAX_REP_PER_EPOCH) revert CapExceeded(); _fundAtCompletion(); uint256 curE = block.timestamp / TREASURY_EPOCH; if (treasurySpendEpoch != curE) { treasurySpendEpoch = curE; treasurySpentInEpoch = 0; } if (treasurySpentInEpoch + BOUNTY > MAX_TREASURY_SPEND_PER_EPOCH) revert CapExceeded(); treasurySpentInEpoch += BOUNTY; if (poolReserve < totalEscrowed + BOUNTY) { if (balanceOf[treasury] < BOUNTY) revert InsufficientFunding(); if (allowance[treasury][address(this)] < BOUNTY) revert TreasuryNoAllowance(); allowance[treasury][address(this)] -= BOUNTY; balanceOf[treasury] -= BOUNTY; balanceOf[address(this)] += BOUNTY; poolReserve += BOUNTY; emit Transfer(treasury, address(this), BOUNTY); } if (poolReserve < totalEscrowed + BOUNTY) revert InsufficientFunding(); if (balanceOf[address(this)] < totalStaked + poolReserve + feeReserve) revert TreasuryEmpty(); treasuryApproved[taskId] = false; delete treasuryApprovalExpiry[taskId]; reviewerSubmitterEpochCount[_pairKey]++; reviewerLastComplete[msg.sender] = block.timestamp; t.completed = true; completedAt[taskId] = block.timestamp; completedBy[taskId]=msg.sender; completionReason[taskId]=reason; escrowed[taskId] = BOUNTY; totalEscrowed += BOUNTY; reviewerEscrowed[msg.sender] += BOUNTY; if (poolReserve < totalEscrowed) revert CapExceeded(); emit BountyEscrowed(taskId, BOUNTY); emit TaskCompleted(taskId); emit TaskCompletedWithReason(taskId, msg.sender, reason); }
 function completeTask(uint256 taskId) external { _complete(taskId, ""); }
 function completeTaskWithReason(uint256 taskId, string calldata reason) external { require(bytes(reason).length <= 1000); _complete(taskId, reason); }
 function disputeTask(uint256 taskId, string calldata reason) external { require(taskId>0 && taskId<=taskCount); Task storage t = tasks[taskId]; if (!t.completed || t.claimed) revert AlreadyDone(); if (msg.sender != t.submitter) revert NotSubmitter(); if (disputed[taskId]) revert AlreadyDone(); if (disputeCount[taskId] >= MAX_DISPUTES_PER_TASK) revert CapExceeded(); if (lastDisputeAt[taskId] != 0 && block.timestamp < lastDisputeAt[taskId] + DISPUTE_COOLDOWN) revert Timelocked(); if (lastDisputeTime[msg.sender] != 0 && block.timestamp < lastDisputeTime[msg.sender] + DISPUTE_COOLDOWN) revert Timelocked(); if (disputeBond == 0) revert NoPending(); if (balanceOf[msg.sender] < disputeBond) revert NotHolder(); balanceOf[msg.sender] -= disputeBond; balanceOf[address(this)] += disputeBond; feeReserve += disputeBond; emit Transfer(msg.sender, address(this), disputeBond); disputeBy[taskId] = msg.sender; disputeBondPaid[taskId] = disputeBond; disputeCount[taskId]++; lastDisputeAt[taskId] = block.timestamp; lastDisputeTime[msg.sender] = block.timestamp; disputed[taskId]=true; disputedAt[taskId]=block.timestamp; disputeReason[taskId]=reason; address rev = completedBy[taskId]; if (rev != address(0)) activeDisputes[rev]++; emit TaskDisputed(taskId, reason); }
 function resolveDispute(uint256 taskId, bool upheld) external nonReentrant { if (guardian != address(0)) { if (msg.sender != guardian) revert NotOwner(); } else { if (msg.sender != owner) revert NotOwner(); } if (!disputed[taskId]) revert NoPending(); if (disputedAt[taskId]==0) revert NoPending(); if (block.timestamp < disputedAt[taskId] + DISPUTE_CHALLENGE_WINDOW) revert Timelocked(); address rev = completedBy[taskId]; Task storage t = tasks[taskId]; address disputer = disputeBy[taskId]; if (disputer == address(0)) revert NoPending(); if (msg.sender == disputer) revert NotOwner(); if (msg.sender == rev) revert SelfDealing(); if (msg.sender == treasury) revert NotTreasury(); if (bytes(disputeReason[taskId]).length == 0) revert NoPending(); uint256 bpaid = disputeBondPaid[taskId]; if (!upheld) { _slashBond(taskId); if (rev != address(0) && activeDisputes[rev] > 0) activeDisputes[rev]--; disputed[taskId]=false; disputedAt[taskId]=0; emit DisputeResolved(taskId, false); return; } if (bpaid > 0 && disputer != address(0)) { if (feeReserve >= bpaid) feeReserve -= bpaid; else feeReserve = 0; balanceOf[address(this)] -= bpaid; balanceOf[disputer] += bpaid; emit Transfer(address(this), disputer, bpaid); emit DisputeBondRefunded(taskId, disputer, bpaid); } disputeBy[taskId]=address(0); disputeBondPaid[taskId]=0; if (rev != t.submitter && rev != address(0)) { uint256 s = staked[rev]; uint256 maxSlash = BOUNTY * 2; uint256 slash = s > maxSlash ? maxSlash : s; if (slash>0) { staked[rev]-=slash; totalStaked-=slash; balanceOf[address(this)]-=slash; balanceOf[treasury]+=slash; emit Transfer(address(this), treasury, slash); emit StakeSlashed(rev, slash); } } if (rev != address(0) && activeDisputes[rev] > 0) activeDisputes[rev]--; treasuryApproved[taskId]=false; delete treasuryApprovalExpiry[taskId]; uint256 esc = escrowed[taskId]; if (esc > 0) { escrowed[taskId]=0; if (totalEscrowed < esc) revert NoPending(); totalEscrowed -= esc; if (poolReserve < totalEscrowed) revert CapExceeded(); if (rev != address(0)) { if (reviewerEscrowed[rev] < esc) revert NoPending(); reviewerEscrowed[rev]-=esc; } t.completed = false; completedAt[taskId]=0; completedBy[taskId]=address(0); completionReason[taskId]=""; _advanceQueue(); } disputed[taskId]=false; disputedAt[taskId]=0; emit DisputeResolved(taskId, true); }
 function expireDispute(uint256 taskId) external { require(taskId > 0 && taskId <= taskCount); if (!disputed[taskId]) revert NoPending(); if (disputedAt[taskId] == 0) revert NoPending(); if (block.timestamp <= disputedAt[taskId] + DISPUTE_EXPIRY) revert NotExpired(); address rev = completedBy[taskId]; if (rev != address(0) && activeDisputes[rev] > 0) activeDisputes[rev]--; disputed[taskId] = false; disputedAt[taskId] = 0; _refundBond(taskId); emit DisputeExpired(taskId); emit DisputeResolved(taskId, false); }
 function _clearExpiredDispute(uint256 taskId) internal { if (disputed[taskId] && disputedAt[taskId] != 0 && block.timestamp > disputedAt[taskId] + DISPUTE_EXPIRY) { address rev = completedBy[taskId]; if (rev != address(0) && activeDisputes[rev] > 0) activeDisputes[rev]--; disputed[taskId] = false; disputedAt[taskId] = 0; _refundBond(taskId); emit DisputeExpired(taskId); emit DisputeResolved(taskId, false); } }
 function _checkQueue(uint256 taskId) internal view { }
 function _advanceQueue() internal { uint256 guard = 100; uint256 n = 0; while (nextPayoutId<=taskCount && n < guard) { Task storage q = tasks[nextPayoutId]; if (q.claimed) { nextPayoutId++; n++; continue; } if (!q.completed) { uint256 sAt = submittedAt[nextPayoutId]; if (sAt != 0 && block.timestamp > sAt + TASK_EXPIRY) { nextPayoutId++; n++; continue; } break; } if (escrowed[nextPayoutId]==0) { nextPayoutId++; n++; continue; } if (disputed[nextPayoutId]) break; uint256 cAt = completedAt[nextPayoutId]; if (cAt != 0 && block.timestamp > cAt + CLAIM_WINDOW) { nextPayoutId++; n++; continue; } break; } }
 function _payBounty(address to, uint256 esc) internal { if (treasuryHalted) revert Paused(); if (esc == 0) revert NoPending(); if (poolReserve < esc) revert InsufficientFunding(); if (poolReserve < totalEscrowed) revert CapExceeded(); if (balanceOf[address(this)] < esc) revert TreasuryEmpty(); poolReserve -= esc; balanceOf[address(this)] -= esc; balanceOf[to] += esc; emit Transfer(address(this), to, esc); }
 function claimTask(uint256 taskId) external nonReentrant { require(taskId > 0 && taskId <= taskCount); if (treasuryHalted) revert Paused(); _clearExpiredDispute(taskId); Task storage t = tasks[taskId]; if (t.submitter != msg.sender) revert NotSubmitter(); if (msg.sender == owner || msg.sender == treasury) revert SelfDealing(); if (t.submitter == owner || t.submitter == treasury) revert SelfDealing(); if (t.claimed) revert AlreadyClaimed(); if (!t.completed) revert NotCompleted(); if (disputed[taskId]) revert Paused(); if (_holding(msg.sender) < MIN_HOLDING) revert NotHolder(); uint256 cAt = completedAt[taskId]; if (cAt == 0) revert NotCompleted(); if (block.timestamp > cAt + CLAIM_WINDOW) revert Expired(); uint256 esc = escrowed[taskId]; if (esc == 0) revert NoPending(); _fundAtClaim(esc); _pullBounty(esc); t.claimed = true; escrowed[taskId] = 0; if (totalEscrowed < esc) revert NoPending(); totalEscrowed -= esc; address rev = completedBy[taskId]; if (rev != address(0)) { if (reviewerEscrowed[rev] < esc) revert NoPending(); reviewerEscrowed[rev] -= esc; } _grantRep(msg.sender); if (openCount[msg.sender] > 0) openCount[msg.sender]--; _payBounty(msg.sender, esc); _advanceQueue(); emit TaskClaimed(taskId, msg.sender, esc); }
 function claimCompensation(uint256 taskId) external nonReentrant { require(taskId > 0 && taskId <= taskCount); if (treasuryHalted) revert Paused(); _clearExpiredDispute(taskId); Task storage t = tasks[taskId]; if (t.submitter != msg.sender) revert NotSubmitter(); if (t.claimed) revert AlreadyClaimed(); if (!t.completed) revert NotCompleted(); if (disputed[taskId]) revert Paused(); if (_holding(msg.sender) < MIN_HOLDING) revert NotHolder(); uint256 cAt = completedAt[taskId]; if (cAt == 0 || block.timestamp <= cAt + CLAIM_WINDOW) revert NotExpired(); uint256 esc = escrowed[taskId]; if (esc == 0) revert NoPending(); if (totalEscrowed < esc) revert NoPending(); _fundAtClaim(esc); _pullBounty(esc); t.claimed = true; escrowed[taskId] = 0; totalEscrowed -= esc; address rev = completedBy[taskId]; if (rev!=address(0)) { if (reviewerEscrowed[rev] < esc) revert NoPending(); reviewerEscrowed[rev]-=esc; } _grantRep(msg.sender); if (openCount[msg.sender] > 0) openCount[msg.sender]--; _payBounty(msg.sender, esc); _advanceQueue(); emit TaskClaimed(taskId, msg.sender, esc); }
 function cleanupStaleEscrow(uint256 taskId) external nonReentrant { require(taskId > 0 && taskId <= taskCount); if (treasuryHalted) revert Paused(); _clearExpiredDispute(taskId); Task storage t = tasks[taskId]; if (!t.completed || t.claimed) revert NoPending(); if (disputed[taskId]) revert Paused(); uint256 cAt = completedAt[taskId]; if (cAt == 0 || block.timestamp <= cAt + CLAIM_WINDOW + CLEANUP_GRACE) revert NotExpired(); uint256 esc = escrowed[taskId]; if (esc == 0) revert NoPending(); if (totalEscrowed < esc) revert NoPending(); _fundAtClaim(esc); _pullBounty(esc); address payee = t.submitter; if (payee == address(0) || payee == owner || payee == treasury) revert SelfDealing(); t.claimed = true; escrowed[taskId] = 0; totalEscrowed -= esc; address rev = completedBy[taskId]; if (rev != address(0)) { if (reviewerEscrowed[rev] < esc) revert NoPending(); reviewerEscrowed[rev] -= esc; } _grantRep(payee); if (openCount[payee] > 0) openCount[payee]--; _payBounty(payee, esc); _advanceQueue(); emit StaleEscrowCleaned(taskId); }
 function cleanupExpiredTask(uint256 taskId) external { require(taskId > 0 && taskId <= taskCount); Task storage t = tasks[taskId]; if (t.completed || t.claimed) revert AlreadyDone(); uint256 sAt = submittedAt[taskId]; if (block.timestamp <= sAt + TASK_EXPIRY) revert NotExpired(); t.claimed = true; address s = t.submitter; if (openCount[s] > 0) openCount[s]--; _advanceQueue(); emit TaskCancelled(taskId); emit TaskCancelReason(taskId, "expired"); }
 function cancelTask(uint256 taskId) external { require(taskId > 0 && taskId <= taskCount); Task storage t = tasks[taskId]; if (t.submitter != msg.sender) revert NotSubmitter(); if (t.completed || t.claimed) revert AlreadyDone(); t.claimed = true; if (openCount[msg.sender] > 0) openCount[msg.sender]--; emit TaskCancelled(taskId); }
 function bulkCancel(uint256[] calldata ids) external { if (msg.sender != owner && !isReviewer[msg.sender]) revert NotOwner(); for (uint256 i = 0; i < ids.length; i++) { uint256 taskId = ids[i]; if (taskId == 0 || taskId > taskCount) continue; Task storage t = tasks[taskId]; if (t.completed || t.claimed) continue; if (msg.sender == t.submitter) continue; uint256 sAt = submittedAt[taskId]; if (block.timestamp <= sAt + TASK_EXPIRY) continue; t.claimed = true; address s = t.submitter; if (openCount[s] > 0) openCount[s]--; emit TaskCancelled(taskId); emit TaskCancelReason(taskId, "expired"); } }
 function expireTask(uint256 taskId) external { if (msg.sender != owner && !isReviewer[msg.sender]) revert NotOwner(); require(taskId > 0 && taskId <= taskCount); Task storage t = tasks[taskId]; if (t.completed || t.claimed) revert AlreadyDone(); if (msg.sender == t.submitter) revert SelfDealing(); uint256 sAt = submittedAt[taskId]; if (block.timestamp <= sAt + TASK_EXPIRY) revert NotExpired(); t.claimed = true; address s = t.submitter; if (openCount[s] > 0) openCount[s]--; emit TaskCancelled(taskId); emit TaskCancelReason(taskId, "expired"); }
 function requestFeeWithdraw(uint256 amount) external { if (msg.sender!=owner && msg.sender!=treasury) revert NotOwner(); if (amount==0 || amount>feeReserve) revert NoPending(); pendingFeeWithdraw=amount; feeWithdrawReadyAt=block.timestamp+withdrawDelay; emit FeeWithdrawRequested(amount, feeWithdrawReadyAt); }
 function requestPoolWithdraw(uint256 amount) external { if (msg.sender!=owner && msg.sender!=treasury) revert NotOwner(); if (amount==0 || amount>poolReserve) revert NoPending(); if (totalEscrowed > poolReserve) revert CapExceeded(); uint256 excess = poolReserve - totalEscrowed; if (amount > excess) revert NoPending(); pendingPoolWithdraw=amount; poolWithdrawReadyAt=block.timestamp+withdrawDelay; emit PoolWithdrawRequested(amount, poolWithdrawReadyAt); }
 function _withdrawFees(address to, uint256 amount) internal { if (treasuryHalted) revert Paused(); if (amount == 0) revert NoPending(); if (amount > feeReserve) revert NoPending(); if (totalEscrowed > poolReserve && poolReserve != 0) revert CapExceeded(); uint256 bal = balanceOf[address(this)]; if (bal < totalStaked + poolReserve + feeReserve) revert TreasuryEmpty(); feeReserve -= amount; balanceOf[address(this)] -= amount; balanceOf[to] += amount; emit Transfer(address(this), to, amount); emit FeesWithdrawn(to, amount); emit FeeWithdrawExecuted(to, amount); }
 function _withdrawPool(address to, uint256 amount) internal { if (treasuryHalted) revert Paused(); if (amount == 0) revert NoPending(); if (amount > poolReserve) revert NoPending(); if (totalEscrowed > poolReserve) revert CapExceeded(); if (amount > poolReserve - totalEscrowed) revert NoPending(); if (balanceOf[address(this)] < totalStaked + feeReserve + poolReserve) revert TreasuryEmpty(); poolReserve -= amount; balanceOf[address(this)] -= amount; balanceOf[to] += amount; emit Transfer(address(this), to, amount); emit PoolWithdrawExecuted(to, amount); }
 function withdrawFees(uint256 amount) external nonReentrant { if (msg.sender != owner && msg.sender != treasury) revert NotOwner(); if (pendingFeeWithdraw != amount || amount == 0) revert Timelocked(); if (block.timestamp < feeWithdrawReadyAt) revert Timelocked(); pendingFeeWithdraw=0; feeWithdrawReadyAt=0; _withdrawFees(msg.sender, amount); }
 function sweepPool(uint256 amount) external nonReentrant { if (msg.sender != treasury) revert NotTreasury(); if (pendingPoolWithdraw != amount || amount == 0) revert Timelocked(); if (block.timestamp < poolWithdrawReadyAt) revert Timelocked(); pendingPoolWithdraw=0; poolWithdrawReadyAt=0; _withdrawPool(msg.sender, amount); }
}