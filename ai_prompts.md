# AI Prompting & Constraint Strategy (CS 457)

This document records the exact system prompts and constraint strategies used to guide AI coding assistants (ChatGPT, Claude, GitHub Copilot) during the design and implementation of the Connect Four networked game application across Sprints 1, 2, and 3.

---

## 1. Constraint Philosophy & AI Policy Compliance

In accordance with course guidelines, AI coding assistants were **strictly constrained** to prevent the generation of generic, unvalidated socket boilerplate. Every generation task was bounded by:
1. **The Custom Wire Protocol:** Forcing the use of newline-delimited (`\n`) UTF-8 JSON payloads adhering strictly to the schema defined in `protocol_blueprint.md`.
2. **Deterministic Stream Framing:** Prohibiting assumptions that `sock.recv()` returns discrete messages, requiring dedicated `bytearray` stream buffer accumulation.
3. **The Finite State Machine (FSM):** Enforcing the exact state transitions (`INIT` $\rightarrow$ `WAITING_FOR_PLAYERS` $\rightarrow$ `GAME_START` $\rightarrow$ `PLAYER_TURN` $\rightleftharpoons$ `EVALUATE_MOVE` $\rightarrow$ `GAME_OVER` $\rightarrow$ `CLEANUP`) modeled in `fsm_specification.md`.
4. **The Concurrency Architecture:** Enforcing single-threaded non-blocking I/O multiplexing via `selectors` as specified in `concurrency_design.md`.
5. **Robust Error & Exception Handling:** Enforcing the TCP 0-byte EOF rule, trapping socket reset/pipe errors, and handling `socket.gaierror` gracefully on DNS resolution failure.

---

## 2. Documented System Prompts

### Prompt 1: Newline-Delimited Frame Serialization (Sprint 1)
> "Write a modular Python function `send_framed_message(sock: socket.socket, message: dict) -> bool` that serializes a dictionary to JSON, appends a `\n` newline delimiter character (0x0A), encodes the payload into UTF-8 bytes, and transmits it across a TCP stream socket using `sendall()`. Do NOT use generic or unconstrained socket code. Trap `ConnectionResetError`, `BrokenPipeError`, and `OSError` to return `False` rather than crashing."

### Prompt 2: Stream Buffer Extraction & Message Delineation (Sprint 1)
> "Write a Python function `extract_messages_from_buffer(buffer: bytearray) -> list[dict]` to extract application messages from a continuous TCP byte-stream. The function must scan the `bytearray` buffer for `\n` delimiters. For every `\n` found, extract the bytes before the delimiter, delete the frame and delimiter from the buffer, decode the frame as UTF-8, and parse it using `json.loads()`. Any partial trailing bytes must remain in the buffer for future `recv()` chunks. In the socket read loop, explicitly check `if not chunk:` to detect TCP 0-byte EOF and avoid infinite CPU loops."

### Prompt 3: Server Concurrency & FSM Game Engine (Sprint 2 & 3)
> "Implement an authoritative Connect Four game server in Python 3 (`server.py`) using non-blocking I/O multiplexing with the standard library `selectors` module (`selectors.DefaultSelector()`).
> Constraints:
> - Parse CLI arguments `-h` (help) and `-p <port>` (required, validating integer range 1024-65535). Bind the listening socket to `0.0.0.0`.
> - Do not use threads, locks, or external third-party libraries. Run sequentially on a single-threaded selector loop.
> - Maintain client sessions in a dictionary mapping `player_id` (1 and 2) to dedicated `ClientSession` objects containing socket descriptor, address, and dedicated `bytearray` buffer.
> - Enforce the 2-player capacity: reject 3rd connections with an `ERROR` message.
> - Implement authoritative Connect Four rules: validate sender ID equals `active_player`, column bounds (1-7), column capacity (top row cell `board[0][col-1] == 0`), simulate gravity drop to the lowest available row, and check horizontal, vertical, and diagonal win/draw conditions.
> - Enforce Sprint 1 FSM transitions and broadcast `STATE_UPDATE` to both clients on move completion.
> - If a client disconnects unexpectedly or sends `DISCONNECT`, award victory by forfeit to the opponent, send `GAME_OVER`, close sockets cleanly, and reset state to `WAITING_FOR_PLAYERS`."

### Prompt 4: Client Application & Graceful DNS Resolution (Sprint 3)
> "Implement a Connect Four CLI game client (`client.py`) in Python 3.
> Constraints:
> - Parse CLI arguments `-h` (help), `-i <server_hostname_or_ip>` (required), and `-p <port>` (required, validating range 1024-65535).
> - Mandatory DNS Error Handling: Resolve the hostname using `socket.gethostbyname()`. Catch `socket.gaierror` explicitly; if caught, print `[ERROR] Unable to resolve DNS hostname '<hostname>'. Please check your Cisco router DNS configuration ('ip dns server' / 'ip host') or verify domain spelling.` and exit cleanly with status code `1`. Do NOT print raw tracebacks.
> - Connect via TCP stream socket, send `{"message_type": "CONNECT"}\n`, and maintain a `bytearray` receive buffer.
> - Render a clean, human-readable ASCII 6x7 grid (`.` for empty, `X` for Player 1, `O` for Player 2).
> - Only prompt for input (`1-7` or `'q'`) when `active_player == my_player_number`. If opponent's turn, display `Waiting for Player X's move...`.
> - Display live scoreboard summaries upon `GAME_OVER`."

### Prompt 5: Automated Verification Test Suite (Sprint 3)
> "Write an automated test suite (`test_connect_four.py`) to verify Sprint 3 requirements without external testing libraries. The suite must test:
> 1. CLI help flags (`-h`), missing required arguments, and out-of-bounds ports.
> 2. DNS resolution failure (`socket.gaierror`) ensuring non-zero exit code 1 and no raw tracebacks.
> 3. Launching the server daemon and two concurrent client sockets over localhost.
> 4. Verifying `LOBBY_WAIT`, `GAME_START`, `STATE_UPDATE`, out-of-turn move rejection with `ERROR`, multiple turns of gravity drops, and disconnect forfeit resolution."

---

## 3. Human Verification & Iteration

Every code artifact produced using these constrained prompts was manually audited:
* **Wire Protocol Compliance:** Confirmed exact JSON key names (`message_type`, `column_number`, `active_player`, `final_game_outcome`, `scores`).
* **Cross-Platform Compatibility:** Replaced Unicode emoji characters with standard ASCII indicators to prevent `charmap` codec encoding errors in Windows CP1252 and minimal CML Linux terminal environments.
* **Socket Unbuffering:** Configured `print(..., flush=True)` to prevent log buffering issues when processes run as background daemons or within CML serial consoles.
