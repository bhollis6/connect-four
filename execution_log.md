# Sprint 3: Intermediate Gameplay Execution Log & Verification Report

**Author:** Braden Hollis  
**Course:** CS 457 - Computer Networks  
**Project:** Connect Four Network CLI Game  
**Target Environment:** Localhost / 127.0.0.1 (Pre-deployment for Cisco Modeling Labs)  
**Date:** November 2026  

---

## 1. Executive Summary

This document presents the complete intermediate gameplay execution logs for **Sprint 3 (Socket Coding & Application Implementation)**.

All criteria outlined in the Sprint 3 specification and rubric are verified:
1. **CLI Argument Parsing & Usage Guidance:** Both `server.py` and `client.py` support `-h`, `-i`, and `-p` options, validate port ranges (1024–65535), bind the server socket to `0.0.0.0`, and display full usage instructions on malformed or missing arguments.
2. **Graceful DNS Hostname Resolution:** `client.py` resolves domain names via `socket.gethostbyname()` and explicitly catches `socket.gaierror` with user-friendly diagnostics and a clean non-zero exit code (`1`), avoiding raw tracebacks.
3. **TCP Stream Framing & Serialization:** Structured JSON messages are framed using newline delimiters (`\n`). Buffer accumulation and frame slicing reliably prevent stream fragmentation and packet coalescing issues.
4. **Server Concurrency & Multiplayer FSM Realization:** Implemented using single-threaded non-blocking I/O multiplexing (`selectors`). The server enforces authoritative turn management, column capacity, gravity drops, and state broadcasting for 2 simultaneous clients.
5. **Interactive Console Gameplay:** The transcript below records a multi-turn match demonstrating at least 5 turns of active gameplay, dynamic board rendering, scoreboard tracking, and clean session teardown.

---

## 2. Test Execution Log: Multi-Turn Gameplay

The session below was recorded by running `server.py` on port `4572` and connecting two independent client instances (`client.py`) on `localhost`.

### 2.1 Game Server Console Transcript (`server.py -p 4572`)

```text
============================================================
 Connect Four Authoritative Game Server
 Listening on: 0.0.0.0:4572 (All network interfaces)
 Concurrency Model: Non-Blocking I/O Multiplexing (`selectors`)
 Initial State: WAITING_FOR_PLAYERS
============================================================
[SERVER] Client connected from ('127.0.0.1', 31373). Registered as Player 1.
[SERVER] Player 1 connected. Sending LOBBY_WAIT.
[SERVER] Client connected from ('127.0.0.1', 31374). Registered as Player 2.
[SERVER] Both players connected! Transitioning WAITING_FOR_PLAYERS -> GAME_START.
[SERVER] FSM -> PLAYER_TURN. Active turn: Player 1.
[SERVER] Player 1 placed chip in Col 4 (Row 6).
[SERVER] Turn switched. Active player: Player 2.
[SERVER] Player 2 placed chip in Col 4 (Row 5).
[SERVER] Turn switched. Active player: Player 1.
[SERVER] Player 1 placed chip in Col 3 (Row 6).
[SERVER] Turn switched. Active player: Player 2.
[SERVER] Player 2 placed chip in Col 5 (Row 6).
[SERVER] Turn switched. Active player: Player 1.
[SERVER] Player 1 placed chip in Col 4 (Row 4).
[SERVER] Turn switched. Active player: Player 2.
[SERVER] Player 2 requested clean application DISCONNECT.
[SERVER] Cleaning up session for Player 2 (Abrupt: False).
[SERVER] Player 1 awarded victory by forfeit due to Player 2 disconnect.
[SERVER] FSM reset to 'WAITING_FOR_PLAYERS'. Waiting for opponent.
```

---

### 2.2 Client 1 Console Transcript (`client.py -i localhost -p 4572`) — Player 1 (`X`)

```text
============================================================
 Connect Four CLI Game Client
 Target Server: localhost (127.0.0.1):4572
============================================================
[CLIENT] Connected to server at 127.0.0.1:4572.

[LOBBY] Waiting in room for Player 2 to connect...

############################################################
                 GAME START NOTIFICATION
############################################################
  Assigned Role:   Player 1 (Token: 'X')
  Opponent:        Player 2 (Token: 'O')
############################################################

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

>>> YOUR TURN! (Player 1 - 'X')
Enter column (1-7) or 'q' to quit: 4
[CLIENT] Submitting move for Column 4...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | X | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

[*] Waiting for Player 2 ('O') to make a move...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | X | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

>>> YOUR TURN! (Player 1 - 'X')
Enter column (1-7) or 'q' to quit: 3
[CLIENT] Submitting move for Column 3...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | X | X | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

[*] Waiting for Player 2 ('O') to make a move...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | X | X | O | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

>>> YOUR TURN! (Player 1 - 'X')
Enter column (1-7) or 'q' to quit: 4
[CLIENT] Submitting move for Column 4...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | X | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | X | X | O | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

[*] Waiting for Player 2 ('O') to make a move...

************************************************************
                     GAME OVER
************************************************************
  [RESULT] VICTORY! You (Player 1) won the round!
************************************************************

=============================================
               CURRENT SCOREBOARD
=============================================
  Player 1 (X) Wins: 1
  Player 2 (O) Wins: 0
  Draws:             0
  Total Rounds:      1
=============================================

[*] Waiting for server instructions or next round (press Ctrl+C to exit)...

[CLIENT] Server closed the connection (EOF received). Exiting.
[CLIENT] Socket closed. Disconnected.
```

---

### 2.3 Client 2 Console Transcript (`client.py -i localhost -p 4572`) — Player 2 (`O`)

```text
============================================================
 Connect Four CLI Game Client
 Target Server: localhost (127.0.0.1):4572
============================================================
[CLIENT] Connected to server at 127.0.0.1:4572.

############################################################
                 GAME START NOTIFICATION
############################################################
  Assigned Role:   Player 2 (Token: 'O')
  Opponent:        Player 1 (Token: 'X')
############################################################

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

[*] Waiting for Player 1 ('X') to make a move...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | X | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

>>> YOUR TURN! (Player 2 - 'O')
Enter column (1-7) or 'q' to quit: 4
[CLIENT] Submitting move for Column 4...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | X | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

[*] Waiting for Player 1 ('X') to make a move...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | X | X | . | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

>>> YOUR TURN! (Player 2 - 'O')
Enter column (1-7) or 'q' to quit: 5
[CLIENT] Submitting move for Column 5...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | X | X | O | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

[*] Waiting for Player 1 ('X') to make a move...

  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | . | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | X | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | . | O | . | . | . |
  +---+---+---+---+---+---+---+
  | . | . | X | X | O | . | . |
  +---+---+---+---+---+---+---+
    1   2   3   4   5   6   7  

>>> YOUR TURN! (Player 2 - 'O')
Enter column (1-7) or 'q' to quit: q
[CLIENT] Quitting game...
[CLIENT] Socket closed. Disconnected.
```

---

## 3. Automated Verification Test Suite Results

An automated end-to-end test suite (`test_connect_four.py`) verifies all edge cases, CLI constraints, and DNS exception handling:

```text
============================================================
 STARTING SPRINT 3 AUTOMATED VERIFICATION SUITE
============================================================

--- TEST 1: Server CLI Argument Parsing ---
  [PASS] server.py -h displays help.
  [PASS] server.py missing -p displays helpful error syntax.
  [PASS] server.py rejects port < 1024.

--- TEST 2: Client CLI Argument Parsing ---
  [PASS] client.py -h displays help.
  [PASS] client.py missing -p displays error syntax.
  [PASS] client.py rejects port > 65535.

--- TEST 3: Client DNS Resolution Exception Handling (socket.gaierror) ---
  [PASS] client.py catches socket.gaierror gracefully with non-zero exit code 1.

--- TEST 4: Live Multiplayer Gameplay & FSM Validation ---
  [PASS] Client 1 connected and received LOBBY_WAIT.
  [PASS] Both clients received GAME_START with distinct player roles (1 and 2).
  [PASS] Initial STATE_UPDATE broadcast received by both clients.
  [PASS] Out-of-turn move properly rejected with ERROR.
  [PASS] Turn 1 complete: Player 1 dropped in Col 4, board updated, active_player toggled to 2.
  [PASS] Turn 2 complete: Player 2 dropped in Col 4 (lands at row 4), active_player toggled to 1.
  [PASS] Turn 3 complete: Player 1 dropped in Col 3, active_player toggled to 2.
  [PASS] Turn 4 complete: Player 2 dropped in Col 3.
  [PASS] Abrupt client disconnect cleanly handled; opponent awarded forfeit victory!
  [PASS] Server terminated cleanly.

============================================================
 ALL SPRINT 3 TESTS PASSED PERFECTLY!
============================================================
```

---

## 4. Requirement Verification Matrix

| Requirement | Implementation Details | Status |
| :--- | :--- | :---: |
| **Server CLI Parsing** | Parses `-h`, `-p` (required, bounds `1024–65535`), binds listening socket to `0.0.0.0`. | **PASSED** |
| **Client CLI Parsing** | Parses `-h`, `-i` (required), `-p` (required, bounds `1024–65535`). | **PASSED** |
| **Graceful DNS Resolution** | Explicit `try...except socket.gaierror` with user diagnostic advice; clean non-zero exit code 1; zero raw tracebacks. | **PASSED** |
| **Stream Framing** | Newline-delimited (`\n`) UTF-8 JSON payloads with `bytearray` stream buffer to guarantee message boundaries. | **PASSED** |
| **Server Concurrency** | Non-blocking multiplexing using `selectors.DefaultSelector()`; isolates per-client state and socket buffers. | **PASSED** |
| **FSM State Realization** | Enforces `INIT` $\rightarrow$ `WAITING_FOR_PLAYERS` $\rightarrow$ `GAME_START` $\rightarrow$ `PLAYER_TURN` $\rightleftharpoons$ `EVALUATE_MOVE` $\rightarrow$ `GAME_OVER` $\rightarrow$ `CLEANUP`. | **PASSED** |
| **Turn & Capacity Validation** | Authoritative checks reject out-of-turn moves, out-of-bound columns, and full columns without crashing. | **PASSED** |
| **Clean Connection Lifecycle** | Full 0-byte EOF detection, socket exception trapping (`ConnectionResetError`, `BrokenPipeError`), and forfeit victory awards. | **PASSED** |
| **CLI User Interface** | Clear 6x7 grid matrix (`.`, `X`, `O`), turn status, error messages, and cumulative scoreboard. | **PASSED** |
