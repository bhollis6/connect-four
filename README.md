# Connect Four - Network CLI Game

**Course:** CS 457 - Computer Networks  
**Author:** Braden Hollis  
**Language:** Python 3.x (Standard Library only - zero external dependencies)  
**Target Environment:** Cisco Modeling Labs (CML) & Local Development  

---

## 1. Project Overview

This repository contains an authoritative, networked two-player **Connect Four** command-line game designed for deployment across a multi-subnet Cisco Modeling Labs (CML) topology.

The implementation strictly translates the specifications designed across previous sprints:
* **Sprint 0:** [Statement of Work (SOW)](sow.md) & Target Domain (`server.hollis.edu`).
* **Sprint 1:** [Application Protocol Blueprint](protocol_blueprint.md) & [Finite State Machine (FSM)](fsm_specification.md).
* **Sprint 2:** [Concurrency Architecture Design](concurrency_design.md) (Non-blocking I/O multiplexing via `selectors`).
* **Sprint 3:** Source code implementation (`server.py`, `client.py`) and [Execution Log](execution_log.md).

---

## 2. Architecture & Design Principles

* **Transport Layer:** TCP stream sockets (`socket.AF_INET`, `socket.SOCK_STREAM`).
* **Packet Framing:** Newline-delimited (`\n`) JSON payloads encoded in UTF-8. A dedicated stream buffer (`bytearray`) accumulates bytes and parses frames, preventing TCP coalescing and fragmentation issues.
* **Server Concurrency:** Single-threaded non-blocking I/O multiplexing using Python's `selectors.DefaultSelector()`. Sockets are set to non-blocking mode (`sock.setblocking(False)`), eliminating race conditions, mutex contention, and deadlocks.
* **Authoritative Turn & State Enforcement:** The server strictly validates that moves originate only from the active player, enforces 1-indexed column boundaries (1–7), simulates gravity piece drops, and detects horizontal, vertical, and diagonal win/draw conditions.
* **Fault Tolerance & Connection Lifecycle:**
  * Handles TCP 0-byte EOF clean closures.
  * Catches low-level socket exceptions (`ConnectionResetError`, `BrokenPipeError`, `OSError`).
  * Gracefully awards victory by forfeit to the remaining connected player upon client departure.
  * Graceful DNS exception handling: `client.py` catches `socket.gaierror` cleanly with diagnostic instructions and non-zero exit code `1`.

---

## 3. Running the Applications

### 3.1 Server Command (`server.py`)

```bash
# Display help instructions
python3 server.py -h

# Start the game server on port 4570 (binds to 0.0.0.0)
python3 server.py -p 4570
```

**Options:**
* `-h`, `--help`: Displays help usage syntax.
* `-p`, `--port`: Listening port number (required, valid range: `1024-65535`).

---

### 3.2 Client Command (`client.py`)

```bash
# Display help instructions
python3 client.py -h

# Connect to local server
python3 client.py -i localhost -p 4570

# Connect to authoritative DNS server hostname (Sprint 4 CML topology)
python3 client.py -i server.hollis.edu -p 4570
```

**Options:**
* `-h`, `--help`: Displays help usage syntax.
* `-i`, `--hostname`: Server DNS hostname or IP address (required).
* `-p`, `--port`: Server port number (required, valid range: `1024-65535`).

---

## 4. Running the Automated Test Suite

A complete test suite validates CLI argument parsing, port boundaries, DNS exception handling, live multi-turn socket gameplay, out-of-turn move rejection, and client forfeit teardown:

```bash
python3 test_connect_four.py
```

---

## 5. Repository Structure

```text
├── server.py                 # Authoritative non-blocking game server (selectors)
├── client.py                 # Interactive Connect Four CLI game client
├── test_connect_four.py      # Automated Sprint 3 test suite
├── execution_log.md          # Multi-turn interactive gameplay execution log
├── sow.md                    # Sprint 0: Statement of Work & Network Blueprint
├── protocol_blueprint.md     # Sprint 1: Wire protocol schemas & framing rules
├── fsm_specification.md      # Sprint 1: Game Finite State Machine (Mermaid)
├── concurrency_design.md     # Sprint 2: Non-blocking selectors architecture & sequence diagrams
├── ai_prompts.md             # Documented system prompts for code generation
├── how_ai_was_used.md        # AI tool usage disclosure
└── README.md                 # Project documentation & run guide
```
