# Sprint 1: Application Protocol Blueprint

## 1. Transport Layer & Packet Framing Mechanism

**Transport Protocol:** TCP  
**Serialization Format:** Structured JSON
**Framing Mechanism:** Newline-Delimited `\n`  

### 1.1 Framing Rule Definition
The receiver knows where one message ends and the next begins by the newline delimiter: `\n`. This solves TCP stream boundaries by delimiting messages in what is otherwise a continuous stream of bytes.

### 1.2 Wire Stream Examples

**Example Stream:**
```text
{"message_type": "CONNECT"}\n{"message_type": "MOVE", "column_number": 3}\n
```

### 1.3 Receiver Extraction Logic

The receiver will look for the `\n` within the byte buffer to split the byte buffer into segments. These segments will be decoded as UTF-8 and parsed as JSON. Data returned by `recv()` is appended to the buffer. Data after the `\n` delimiter is not parsed until a following `\n` delimiter arrives to ensure messages are complete.

## 2. Application Message Types

### 2.1 CONNECT
* **Direction:** Client $\rightarrow$ Server
* **Purpose:** Client requests to join the game room.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "CONNECT"
* **Sample Payload:**
  ```json
  {
    "message_type": "CONNECT",
  }
  ```

### 2.2 LOBBY_WAIT
* **Direction:** Server $\rightarrow$ Client
* **Purpose:** Server notifies the first connected client that it is waiting for Player 2.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "LOBBY_WAIT"
* **Sample Payload:**
  ```json
  {
    "message_type": "LOBBY_WAIT",
  }
  ```

### 2.3 GAME_START
* **Direction:** Server $\rightarrow$ Clients
* **Purpose:** Server notifies both clients the game has started and assigns player numbers.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "GAME_START"
  * `player_number` (int): Randomly assigned, mutually exclusive value (either 1 or 2)
* **Sample Payload:**
  ```json
  {
    "message_type": "GAME_START",
    "player_number": 1
  }
  ```

### 2.4 MOVE
* **Direction:** Client $\rightarrow$ Server
* **Purpose:** Active player submits a column choice for Connect Four.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "MOVE"
  * `column_number` (int): Value from 1 to 7 (corresponding to the number of columns on a Connect Four board)
* **Sample Payload:**
  ```json
  {
    "message_type": "MOVE",
    "column_number": 6
  }
  ```

### 2.5 STATE_UPDATE
* **Direction:** Server $\rightarrow$ Clients
* **Purpose:** Server broadcasts updated board state, scores, and active player turn.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "STATE_UPDATE"
  * `board` (list of lists): Current board state of size 6x7
  * `active_player` (int): Either 1 or 2
* **Sample Payload:**
  ```json
  {
    "message_type": "STATE_UPDATE",
    "board": [[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 2, 2, 0], [0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 2, 2, 0], [0, 0, 0, 0, 1, 1, 0]],
    "active_player": 1
  }
  ```

### 2.6 ERROR
* **Direction:** Server $\rightarrow$ Client
* **Purpose:** Server notifies a client of an out-of-turn move, full column, or miscellaneous error.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "ERROR"
  * `error_message`(string): Describes the error
* **Sample Payload:**
  ```json
  {
    "message_type": "ERROR",
    "error_message": "Your move's selected column is full."
  }
  ```

### 2.7 DISCONNECT
* **Direction:** Client $\rightarrow$ Server
* **Purpose:** Client notifies server of an graceful exit.
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "DISCONNECT"
* **Sample Payload:**
  ```json
  {
    "message_type": "DISCONNECT"
  }
  ```

### 2.8 GAME_OVER
* **Direction:** Server $\rightarrow$ Clients
* **Purpose:** Server broadcasts final game outcome (Win, Draw, Forfeit).
* **Schema / Data Types:**
  * `message_type` (string): Fixed value "GAME_OVER"
  * `final_game_outcome` (int): 0 (draw), 1 (player 1 wins), 2 "player 2 wins"
* **Sample Payload:**
  ```json
  {
    "message_type": "GAME_OVER",
    "final_game_outcome": 1
  }
  ```

---

## 3. Connection Termination & Socket Lifecycle

### 3.1 Graceful Application Disconnection
If a client tries to quit, it sends a `DISCONNECT` message. The server reads this message, broadcasts a `GAME_OVER` message, and the remaining player wins by forfeit. Lastly, the server closes the connection with `sock.close()` and transitions to the `CLEANUP` state.

### 3.2 TCP EOF Detection (The 0-Byte Rule)
The server will always check if `sock.recv()` returns an empty byte string. If this was not checked, the `sock.recv()` would continue to return an empty byte string, consuming 100% CPU with an infinite loop.

### 3.3 Abrupt Termination & Socket Exceptions
If a client crashes or drops off the network without sending a TCP FIN, the server's `send()` or `recv()` will raise an exception. A try-except block is used to catch `ConnectionResetError` or `BrokenPipeError`. Then, the server logs the error, cleans up, and declares the winner by forfeit.
