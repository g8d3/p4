#!/usr/bin/env python3
"""FiloEterno auditor exam (Phase 2): known-vulnerable contracts, ground truth.
NOT self-graded — each case has a known bug class; keyword match + human check.
Usage: exam.py   (3 model calls)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from loop import call_model, extract_json  # noqa: E402

NEEDS = json.load(open(os.path.join(ROOT, "needs.json")))
DATA = os.path.join(ROOT, "data")

CASES = [
    ("reentrancy-vault",
     "reentr",
     """pragma solidity 0.8.26;
contract UnsafeVault {
    mapping(address => uint256) public balances;
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "low");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send fail");
        balances[msg.sender] -= amount;
    }
}"""),
    ("txorigin-auth",
     "tx.origin",
     """pragma solidity 0.8.26;
contract TxOriginWallet {
    address public owner;
    constructor() { owner = msg.sender; }
    function drain() external {
        require(tx.origin == owner, "not owner");
        (bool ok, ) = msg.sender.call{value: address(this).balance}("");
        require(ok);
    }
    receive() external payable {}
}"""),
    ("open-mint",
     "mint",
     """pragma solidity 0.8.26;
contract OpenMint {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }
}"""),
]


def main():
    results = []
    for name, keyword, src in CASES:
        raw = call_model("You audit this Solidity 0.8.26 contract. List every vulnerability. "
                         "Reply JSON only: {\"findings\": [{\"severity\": \"critical|high|medium|low|info\", "
                         "\"title\": \"...\", \"detail\": \"...\"}]}.\nSOURCE:\n" + src,
                         max_tokens=8000)
        try:
            d = extract_json(raw)
            findings = d.get("findings", []) if d else []
        except (AttributeError, ValueError):
            findings = []
        blob = json.dumps(findings).lower()
        caught = keyword in blob
        results.append({"case": name, "expected": keyword, "caught": caught,
                        "n_findings": len(findings)})
        print(f"{name}: expected '{keyword}' -> {'CAUGHT' if caught else 'MISSED'} "
              f"({len(findings)} findings)")
    score = sum(1 for r in results if r["caught"])
    with open(os.path.join(DATA, "exam.jsonl"), "a") as f:
        f.write(json.dumps({"results": results, "score": f"{score}/{len(results)}"}) + "\n")
    with open(NEEDS["lessons_file"], "a") as f:
        from loop import now
        f.write(f"\n## {now()} auditor exam: {score}/{len(results)} known bugs caught\n" +
                "".join(f"- {r['case']}: {'CAUGHT' if r['caught'] else 'MISSED'}\n" for r in results))
    print(f"exam score: {score}/{len(results)}")


if __name__ == "__main__":
    main()
