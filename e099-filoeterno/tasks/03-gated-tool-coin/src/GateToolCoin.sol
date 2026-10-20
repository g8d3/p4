// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

contract GateToolCoin {
    string public name = "Gate Tool Coin";
    string public symbol = "GTC";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    address public owner;
    address public pendingOwner;
    address public treasury;
    address public reviewer;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public constant FEE_BPS = 50;
    uint256 public constant MIN_HOLDING = 5000 * 1e18;
    uint256 public constant BOUNTY = 50 * 1e18;
    uint256 public constant MAX_OPEN = 3;
    uint256 public maxDescLen = 2000;
    uint256 public submitFee;
    uint256 public holdDelay;
    uint256 public claimDelay;
    uint256 public maxTotalBounties = 200000 * 1e18;
    uint256 public totalPaid;
    bool public paused;
    uint256 public maxSubmitsPerBlock = 20;
    uint256 public lastSubmitBlock;
    uint256 public submitsInBlock;
    mapping(address => uint256) public holderSince;
    struct Task {
        uint256 id;
        address submitter;
        string description;
        bool completed;
        bool claimed;
    }
    uint256 public taskCount;
    mapping(uint256 => Task) public tasks;
    mapping(uint256 => uint256) public taskBounty;
    mapping(uint256 => uint256) public completedAt;
    mapping(uint256 => bool) public ownerApproved;
    mapping(uint256 => bool) public reviewerApproved;
    mapping(address => uint256) public openCount;
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
    error RateLimited();
    error DescTooLong();
    error TooEarly();
    error CapExceeded();
    error SelfVerify();
    error OwnerTaskBlocked();
    error NotPendingOwner();
    error ZeroAddress();
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event TaskSubmitted(uint256 indexed id, address indexed submitter, string description);
    event TaskCompleted(uint256 indexed id);
    event TaskApproved(uint256 indexed id, address indexed approver);
    event TaskClaimed(uint256 indexed id, address indexed claimer, uint256 bounty);
    event ReviewerSet(address indexed reviewer);
    event OwnershipTransferStarted(address indexed oldOwner, address indexed newOwner);
    event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);
    constructor(address _treasury) {
        require(_treasury != address(0));
        owner = msg.sender;
        treasury = _treasury;
        totalSupply = 1_000_000 * 1e18;
        balanceOf[owner] = totalSupply;
        holderSince[owner] = block.timestamp;
        emit Transfer(address(0), owner, 1_000_000 * 1e18);
    }
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }
    function acceptOwnership() external {
        if (msg.sender != pendingOwner) revert NotPendingOwner();
        address oldOwner = owner;
        owner = pendingOwner;
        pendingOwner = address(0);
        if (balanceOf[owner] >= MIN_HOLDING && holderSince[owner] == 0) holderSince[owner] = block.timestamp;
        emit OwnershipTransferred(oldOwner, owner);
    }
    function setReviewer(address _reviewer) external onlyOwner {
        require(_reviewer != owner);
        reviewer = _reviewer;
        emit ReviewerSet(_reviewer);
    }
    function setPaused(bool _paused) external onlyOwner { paused = _paused; }
    function setSubmitFee(uint256 _fee) external onlyOwner { submitFee = _fee; }
    function setHoldDelay(uint256 _d) external onlyOwner { holdDelay = _d; }
    function setClaimDelay(uint256 _d) external onlyOwner { claimDelay = _d; }
    function setMaxDescLen(uint256 _l) external onlyOwner { require(_l > 0); maxDescLen = _l; }
    function setMaxSubmitsPerBlock(uint256 _m) external onlyOwner { require(_m > 0); maxSubmitsPerBlock = _m; }
    function setMaxTotalBounties(uint256 _m) external onlyOwner { maxTotalBounties = _m; }
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(allowance[from][msg.sender] >= amount);
        allowance[from][msg.sender] -= amount;
        _transfer(from, to, amount);
        return true;
    }
    function _updateHolderSince(address a) internal {
        if (balanceOf[a] >= MIN_HOLDING) {
            if (holderSince[a] == 0) holderSince[a] = block.timestamp;
        } else {
            holderSince[a] = 0;
        }
    }
    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0));
        require(to != address(0));
        require(balanceOf[from] >= amount);
        uint256 fee = amount * FEE_BPS / 10000;
        uint256 net = amount - fee;
        balanceOf[from] -= amount;
        balanceOf[to] += net;
        balanceOf[treasury] += fee;
        _updateHolderSince(from);
        _updateHolderSince(to);
        if (to == treasury || from == treasury) _updateHolderSince(treasury);
        else if (balanceOf[treasury] >= MIN_HOLDING && holderSince[treasury] == 0) holderSince[treasury] = block.timestamp;
        if (fee > 0) {
            emit Transfer(from, treasury, fee);
        }
        emit Transfer(from, to, net);
    }
    function submitTask(string calldata description) external returns (uint256) {
        if (paused) revert Paused();
        if (balanceOf[msg.sender] < MIN_HOLDING) revert NotHolder();
        if (holderSince[msg.sender] == 0) {
            if (holdDelay == 0) holderSince[msg.sender] = block.timestamp;
            else revert NotHolder();
        }
        if (holdDelay > 0 && block.timestamp < holderSince[msg.sender] + holdDelay) revert NotHolder();
        require(bytes(description).length > 0);
        if (bytes(description).length > maxDescLen) revert DescTooLong();
        if (block.number != lastSubmitBlock) { lastSubmitBlock = block.number; submitsInBlock = 0; }
        if (submitsInBlock >= maxSubmitsPerBlock) revert RateLimited();
        submitsInBlock++;
        if (openCount[msg.sender] >= MAX_OPEN) revert TooManyOpen();
        if (submitFee > 0) {
            require(balanceOf[msg.sender] >= submitFee + MIN_HOLDING || balanceOf[msg.sender] - submitFee >= 0);
            require(balanceOf[msg.sender] >= submitFee);
            balanceOf[msg.sender] -= submitFee;
            totalSupply -= submitFee;
            emit Transfer(msg.sender, address(0), submitFee);
            _updateHolderSince(msg.sender);
            if (balanceOf[msg.sender] < MIN_HOLDING) revert NotHolder();
        }
        taskCount++;
        uint256 id = taskCount;
        tasks[id] = Task({id: id, submitter: msg.sender, description: description, completed: false, claimed: false});
        taskBounty[id] = BOUNTY;
        openCount[msg.sender]++;
        emit TaskSubmitted(id, msg.sender, description);
        return id;
    }
    function completeTask(uint256 taskId) external {
        if (msg.sender != owner && (reviewer == address(0) || msg.sender != reviewer)) revert NotOwner();
        require(taskId > 0 && taskId <= taskCount);
        if (tasks[taskId].completed) revert AlreadyDone();
        address submitter = tasks[taskId].submitter;
        if (submitter == msg.sender) revert SelfVerify();
        if (submitter == owner) revert OwnerTaskBlocked();
        if (submitter == reviewer) revert OwnerTaskBlocked();
        if (reviewer == address(0)) {
            tasks[taskId].completed = true;
            completedAt[taskId] = block.timestamp;
            openCount[submitter]--;
            emit TaskCompleted(taskId);
        } else {
            if (msg.sender == owner) ownerApproved[taskId] = true;
            else reviewerApproved[taskId] = true;
            emit TaskApproved(taskId, msg.sender);
            if (!ownerApproved[taskId] || !reviewerApproved[taskId]) return;
            tasks[taskId].completed = true;
            completedAt[taskId] = block.timestamp;
            openCount[submitter]--;
            emit TaskCompleted(taskId);
        }
    }
    function claimTask(uint256 taskId) external {
        if (tasks[taskId].submitter != msg.sender) revert NotSubmitter();
        if (!tasks[taskId].completed) revert NotCompleted();
        if (tasks[taskId].claimed) revert AlreadyClaimed();
        if (msg.sender == owner || msg.sender == reviewer) revert OwnerTaskBlocked();
        if (block.timestamp < completedAt[taskId] + claimDelay) revert TooEarly();
        if (balanceOf[msg.sender] < MIN_HOLDING) revert NotHolder();
        if (holdDelay > 0 && (holderSince[msg.sender] == 0 || block.timestamp < holderSince[msg.sender] + holdDelay)) revert NotHolder();
        uint256 bounty = taskBounty[taskId];
        if (bounty == 0) bounty = BOUNTY;
        if (balanceOf[treasury] < bounty) revert TreasuryEmpty();
        if (allowance[treasury][address(this)] < bounty) revert TreasuryNoAllowance();
        if (totalPaid + bounty > maxTotalBounties) revert CapExceeded();
        allowance[treasury][address(this)] -= bounty;
        balanceOf[treasury] -= bounty;
        balanceOf[msg.sender] += bounty;
        totalPaid += bounty;
        _updateHolderSince(treasury);
        _updateHolderSince(msg.sender);
        emit Transfer(treasury, msg.sender, bounty);
        emit TaskClaimed(taskId, msg.sender, bounty);
        tasks[taskId].claimed = true;
    }
}
