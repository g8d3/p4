// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

contract LotteryCoin {
    string public name = "Lottery";
    string public symbol = "LOTTO";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    address public owner;
    uint256 public constant ROUND = 7 days;
    uint256 public constant MIN_ENTRY_BALANCE = 1000 * 10**18;
    uint256 public startTime;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    mapping(uint256 => uint256) public roundFees;
    mapping(uint256 => address[]) private _entries;
    mapping(uint256 => mapping(address => bool)) public hasEntered;
    mapping(uint256 => address) public roundWinner;
    mapping(uint256 => uint256) public roundPrize;
    mapping(uint256 => bool) public roundDrawn;
    mapping(uint256 => bool) public roundClaimed;
    mapping(uint256 => uint256) public roundRequestBlock;
    bool private _locked;
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event FeeCollected(address indexed from, address indexed to, uint256 fee, uint256 indexed roundId);
    event Entered(uint256 indexed roundId, address indexed user);
    event WinnerDrawn(uint256 indexed roundId, address indexed winner, uint256 prize);
    event DrawRequested(uint256 indexed roundId, uint256 requestBlock);
    event PrizeClaimed(uint256 indexed roundId, address indexed winner, uint256 amount);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }
    modifier nonReentrant() { require(!_locked, "reentrant"); _locked = true; _; _locked = false; }
    constructor() {
        owner = msg.sender;
        startTime = block.timestamp;
        totalSupply = 1000000 * 10**18;
        _balances[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    function balanceOf(address account) external view returns (uint256) { return _balances[account]; }
    function allowance(address o, address s) external view returns (uint256) { return _allowances[o][s]; }
    function approve(address spender, uint256 amount) external returns (bool) {
        require(msg.sender != address(0), "zero sender");
        require(spender != address(0), "zero spender");
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    function transfer(address to, uint256 amount) external returns (bool) {
        _transferWithFee(msg.sender, to, amount);
        return true;
    }
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(from != address(0), "zero from");
        require(to != address(0), "zero to");
        uint256 allowed = _allowances[from][msg.sender];
        require(allowed >= amount, "allowance exceeded");
        if (allowed != type(uint256).max) { _allowances[from][msg.sender] = allowed - amount; }
        _transferWithFee(from, to, amount);
        return true;
    }
    function _transferWithFee(address from, address to, uint256 amount) internal {
        require(from != address(0), "zero from");
        require(to != address(0), "zero to");
        require(_balances[from] >= amount, "balance exceeded");
        uint256 fee = amount / 100;
        uint256 net = amount - fee;
        _balances[from] -= amount;
        _balances[to] += net;
        emit Transfer(from, to, net);
        if (fee > 0) {
            _balances[address(this)] += fee;
            emit Transfer(from, address(this), fee);
            uint256 r = getCurrentRound();
            roundFees[r] += fee;
            emit FeeCollected(from, to, fee, r);
        }
    }
    function getCurrentRound() public view returns (uint256) {
        if (block.timestamp < startTime) return 0;
        return (block.timestamp - startTime) / ROUND;
    }
    function getEntryCount(uint256 roundId) external view returns (uint256) { return _entries[roundId].length; }
    function getEntries(uint256 roundId) external view returns (address[] memory) { return _entries[roundId]; }
    function enter() external {
        uint256 r = getCurrentRound();
        require(_balances[msg.sender] >= MIN_ENTRY_BALANCE, "need 1000 tokens");
        require(!hasEntered[r][msg.sender], "already entered");
        hasEntered[r][msg.sender] = true;
        _entries[r].push(msg.sender);
        emit Entered(r, msg.sender);
    }
    function drawWinner(uint256 roundId) external {
        require(!roundDrawn[roundId], "already drawn");
        require(roundRequestBlock[roundId] == 0, "already drawn");
        require(block.timestamp >= startTime + (roundId + 1) * ROUND, "round not ended");
        uint256 len = _entries[roundId].length;
        require(len > 0, "no entries");
        roundRequestBlock[roundId] = block.number;
        emit DrawRequested(roundId, block.number);
    }
    function finalizeWinner(uint256 roundId) external {
        uint256 requestBlock = roundRequestBlock[roundId];
        require(requestBlock != 0, "not committed");
        require(!roundDrawn[roundId], "already drawn");
        require(block.number >= requestBlock + 5, "too early");
        require(blockhash(requestBlock) != bytes32(0), "blockhash expired");
        uint256 len = _entries[roundId].length;
        require(len > 0, "no entries");
        uint256 idx = uint256(blockhash(requestBlock)) % len;
        address winner = _entries[roundId][idx];
        if (_balances[winner] >= MIN_ENTRY_BALANCE) {
            require(winner != address(0), "zero winner");
            roundWinner[roundId] = winner;
            roundDrawn[roundId] = true;
            uint256 prize = (roundFees[roundId] * 90) / 100;
            roundPrize[roundId] = prize;
            emit WinnerDrawn(roundId, winner, prize);
        } else {
            address redrawn = address(0);
            for (uint256 i = 1; i < len; i++) {
                address cand = _entries[roundId][(idx + i) % len];
                if (_balances[cand] >= MIN_ENTRY_BALANCE) {
                    redrawn = cand;
                    break;
                }
            }
            if (redrawn != address(0)) {
                roundWinner[roundId] = redrawn;
                roundDrawn[roundId] = true;
                uint256 prize = (roundFees[roundId] * 90) / 100;
                roundPrize[roundId] = prize;
                emit WinnerDrawn(roundId, redrawn, prize);
            } else {
                uint256 fees = roundFees[roundId];
                roundDrawn[roundId] = true;
                roundWinner[roundId] = address(0);
                roundPrize[roundId] = 0;
                if (fees > 0) {
                    roundFees[roundId + 1] += fees;
                    roundFees[roundId] = 0;
                }
                emit WinnerDrawn(roundId, address(0), 0);
            }
        }
    }
    function claimPrize(uint256 roundId) external nonReentrant {
        require(roundDrawn[roundId], "not drawn");
        require(!roundClaimed[roundId], "already claimed");
        address winner = roundWinner[roundId];
        require(winner != address(0), "zero winner");
        require(msg.sender == winner, "not winner");
        uint256 prize = roundPrize[roundId];
        require(prize > 0, "zero prize");
        require(_balances[address(this)] >= prize, "insufficient pool");
        roundClaimed[roundId] = true;
        _balances[address(this)] -= prize;
        _balances[winner] += prize;
        emit Transfer(address(this), winner, prize);
        emit PrizeClaimed(roundId, winner, prize);
    }
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}
