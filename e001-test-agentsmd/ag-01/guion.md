# Script: File-based multi-agent system

Estimated duration: ~2 min 30 sec

---

## 1. Introduction (30 sec)

"Imagine a multi-agent system where agents don't need a database, a message bus, or a central orchestrator. Just files and directories.

That is exactly what we are building here. A system where each agent reads an AGENTS.md file, knows what to do, writes its results, and the next agent picks up from there.

Welcome to P4."

## 2. Structure (45 sec)

"The structure is simple. At the root we have an AGENTS.md that explains the global rules. Then each experiment lives in its own directory with e-number-name format.

For example, the current experiment is e001-test-agentsmd. Inside, another AGENTS.md explains what this specific experiment does. And if multiple agents are working, each one has its own subdirectory: ag-01, ag-02, and so on.

Each agent defines its own internal structure. No restrictions. Total freedom to organize."

## 3. Comparison (30 sec)

"Before, a typical multi-agent system required a database for persistence, a message bus for communication, and an orchestrator for coordination.

Here we eliminate all of that. The file system is the database. The directories are the message bus. And the AGENTS.md is the orchestrator. Less infrastructure, fewer failure points, simpler."

## 4. Demo (30 sec)

"Here is the live structure. I will navigate through the directories to show it. [show tree] Notice how each level has its own AGENTS.md. This allows any agent — human or AI — to arrive, read, and know exactly what to do without external context."

## 5. Closing (15 sec)

"This is the philosophy of P4: simple systems that work. No over-engineering. No unnecessary infrastructure. Just files, directories, and well-informed agents."

---

## Technical notes

- TTS: Colombian voice, Latin American Spanish
- Format: 9:16 vertical
- Duration: keep each section within estimated time
- Transitions: 1.5 sec pause between sections
