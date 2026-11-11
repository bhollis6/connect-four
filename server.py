#!/usr/bin/env python3
"""
Connect Four Network Game Server (CS 457 Sprint 3)

Author: Braden Hollis
Course: CS 457 - Computer Networks
Environment: Python 3.x (Compatible with CML Linux nodes and local developer machines)

Architectural Overview:
- Transport Layer: TCP stream sockets (AF_INET, SOCK_STREAM)
- Framing: Newline-delimited ('\\n') JSON payloads (UTF-8 encoded)
- Concurrency Model: Non-blocking I/O multiplexing using the `selectors` module
- FSM Lifecycle: INIT -> WAITING_FOR_PLAYERS -> GAME_START -> PLAYER_TURN <-> EVALUATE_MOVE -> GAME_OVER -> CLEANUP
- Network Address: Binds to 0.0.0.0 on a user-specified port (1024-65535)
"""

import argparse
import functools
import json
import selectors
import socket
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Ensure all prints are unbuffered for real-time daemon logging
print = functools.partial(print, flush=True)

BOARD_ROWS = 6
BOARD_COLS = 7


class CustomArgumentParser(argparse.ArgumentParser):
    """Argument parser that prints full help usage on missing/malformed arguments."""

    def error(self, message: str) -> None:
        sys.stderr.write(f"\n[ERROR] {message}\n\n")
        self.print_help(sys.stderr)
        sys.exit(2)


def validate_port(port_val: int) -> int:
    """Validates that the specified port is within the valid unprivileged range (1024-65535)."""
    if not (1024 <= port_val <= 65535):
        raise argparse.ArgumentTypeError(
            f"Port {port_val} out of range. Port must be between 1024 and 65535."
        )
    return port_val


@dataclass
class ClientSession:
    """Represents an active client session connected to the game server."""

    sock: socket.socket
    addr: Tuple[str, int]
    player_id: int
    buffer: bytearray = field(default_factory=bytearray)


def send_framed_message(sock: socket.socket, message: dict) -> bool:
    """
    Serializes a dictionary to JSON, appends a newline delimiter ('\\n'),
    encodes to UTF-8, and transmits across the stream using sendall().
    Returns True on success, False if connection drop occurred.
    """
    try:
        wire_payload = json.dumps(message) + "\n"
        sock.sendall(wire_payload.encode("utf-8"))
        return True
    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
        print(f"[SERVER WARNING] Failed to send message to socket: {e}")
        return False


def extract_messages_from_buffer(buffer: bytearray) -> List[dict]:
    """
    Scans a bytearray stream buffer for newline delimiters ('\\n').
    Extracts all fully-received JSON messages and trims them from the buffer.
    Incomplete frames remain in the buffer for future recv() chunks.
    """
    messages = []
    while True:
        pos = buffer.find(b"\n")
        if pos == -1:
            break
        frame_bytes = buffer[:pos]
        del buffer[: pos + 1]
        line = frame_bytes.decode("utf-8", errors="replace").strip()
        if line:
            try:
                parsed = json.loads(line)
                messages.append(parsed)
            except json.JSONDecodeError as err:
                print(f"[SERVER WARNING] Malformed JSON received: {line} ({err})")
    return messages


def check_winner(board: List[List[int]]) -> int:
    """
    Evaluates the 6x7 grid for Connect Four victory conditions:
    horizontal, vertical, diagonal down-right, and diagonal up-right.
    Returns:
        1 if Player 1 won,
        2 if Player 2 won,
        0 if no winner detected yet.
    """
    # 1. Horizontal check
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS - 3):
            val = board[r][c]
            if val != 0 and val == board[r][c + 1] == board[r][c + 2] == board[r][c + 3]:
                return val

    # 2. Vertical check
    for r in range(BOARD_ROWS - 3):
        for c in range(BOARD_COLS):
            val = board[r][c]
            if val != 0 and val == board[r + 1][c] == board[r + 2][c] == board[r + 3][c]:
                return val

    # 3. Diagonal down-right check (\)
    for r in range(BOARD_ROWS - 3):
        for c in range(BOARD_COLS - 3):
            val = board[r][c]
            if (
                val != 0
                and val == board[r + 1][c + 1] == board[r + 2][c + 2] == board[r + 3][c + 3]
            ):
                return val

    # 4. Diagonal up-right check (/)
    for r in range(3, BOARD_ROWS):
        for c in range(BOARD_COLS - 3):
            val = board[r][c]
            if (
                val != 0
                and val == board[r - 1][c + 1] == board[r - 2][c + 2] == board[r - 3][c + 3]
            ):
                return val

    return 0


def is_board_full(board: List[List[int]]) -> bool:
    """Returns True if all columns are filled at row 0 (top row), indicating a draw."""
    return all(board[0][c] != 0 for c in range(BOARD_COLS))


def drop_piece(board: List[List[int]], col_idx: int, player_num: int) -> int:
    """
    Drops a player's piece into the specified column (0-indexed).
    Gravity simulates dropping to the lowest empty row.
    Returns the row index where piece landed, or -1 if column is full.
    """
    for r in range(BOARD_ROWS - 1, -1, -1):
        if board[r][col_idx] == 0:
            board[r][col_idx] = player_num
            return r
    return -1


class ConnectFourServer:
    """
    Non-blocking multiplexed Connect Four Game Server utilizing `selectors`.
    Enforces authoritative state management, turn alternation, and scoreboard tracking.
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()
        self.server_sock: Optional[socket.socket] = None
        self.client_sessions: Dict[int, ClientSession] = {}
        self.board: List[List[int]] = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.fsm_state = "INIT"
        self.active_player = 1
        self.starting_player = 1
        self.running = False

        # Persistent session scoreboard across multiple rounds
        self.match_scores = {
            "player_1_wins": 0,
            "player_2_wins": 0,
            "draws": 0,
            "rounds_played": 0,
        }

    def start(self) -> None:
        """Initializes the TCP server socket, binds to 0.0.0.0, and enters the selector loop."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.server_sock.setblocking(False)

        # Register server listening socket with selector for read events (incoming connections)
        self.selector.register(self.server_sock, selectors.EVENT_READ, data=None)
        self.fsm_state = "WAITING_FOR_PLAYERS"
        self.running = True

        print("=" * 60)
        print(" Connect Four Authoritative Game Server")
        print(f" Listening on: {self.host}:{self.port} (All network interfaces)")
        print(f" Concurrency Model: Non-Blocking I/O Multiplexing (`selectors`)")
        print(f" Initial State: {self.fsm_state}")
        print("=" * 60)

        try:
            while self.running:
                events = self.selector.select(timeout=1.0)
                for key, mask in events:
                    if key.data is None:
                        self._accept_connection(key.fileobj)
                    else:
                        self._service_client(key, mask)
        except KeyboardInterrupt:
            print("\n[SERVER] Server shutting down by admin request (Ctrl+C)...")
        finally:
            self._cleanup_all()

    def _accept_connection(self, listener_sock: socket.socket) -> None:
        """Accepts a new incoming client connection."""
        try:
            client_sock, addr = listener_sock.accept()
        except BlockingIOError:
            return

        # Capacity check: Only 2 active players permitted in a game room
        if len(self.client_sessions) >= 2:
            print(f"[SERVER] Rejecting connection from {addr}: Game room capacity reached (2/2).")
            send_framed_message(
                client_sock,
                {
                    "message_type": "ERROR",
                    "error_message": "Game room full. Only 2 players allowed.",
                },
            )
            client_sock.close()
            return

        client_sock.setblocking(False)

        # Assign lowest available player ID (1 or 2)
        assigned_id = 1 if 1 not in self.client_sessions else 2
        session = ClientSession(sock=client_sock, addr=addr, player_id=assigned_id)
        self.client_sessions[assigned_id] = session

        self.selector.register(client_sock, selectors.EVENT_READ, data=session)
        print(f"[SERVER] Client connected from {addr}. Registered as Player {assigned_id}.")

    def _service_client(self, key: selectors.SelectorKey, mask: int) -> None:
        """Services read events on a registered client socket."""
        session: ClientSession = key.data
        sock: socket.socket = session.sock

        if mask & selectors.EVENT_READ:
            try:
                chunk = sock.recv(1024)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                print(f"[SERVER] Abrupt socket drop for Player {session.player_id}: {e}")
                self._handle_client_disconnect(session, abrupt=True)
                return

            # TCP EOF detection: 0-byte chunk indicates peer closed write half (clean FIN)
            if not chunk:
                print(f"[SERVER] TCP EOF received (0-bytes) from Player {session.player_id}.")
                self._handle_client_disconnect(session, abrupt=False)
                return

            session.buffer.extend(chunk)
            messages = extract_messages_from_buffer(session.buffer)
            for msg in messages:
                self._dispatch_message(session, msg)

    def _dispatch_message(self, session: ClientSession, msg: dict) -> None:
        """Processes a single deserialized message from a client according to the FSM."""
        msg_type = msg.get("message_type")
        sender_id = session.player_id

        if msg_type == "CONNECT":
            self._handle_connect(session)

        elif msg_type == "MOVE":
            self._handle_move(session, msg)

        elif msg_type == "DISCONNECT":
            print(f"[SERVER] Player {sender_id} requested clean application DISCONNECT.")
            self._handle_client_disconnect(session, abrupt=False)

        else:
            print(f"[SERVER WARNING] Unrecognized message type '{msg_type}' from Player {sender_id}.")
            send_framed_message(
                session.sock,
                {
                    "message_type": "ERROR",
                    "error_message": f"Unrecognized message_type: '{msg_type}'.",
                },
            )

    def _handle_connect(self, session: ClientSession) -> None:
        """Handles a CONNECT message from a client."""
        sender_id = session.player_id

        if len(self.client_sessions) < 2:
            self.fsm_state = "WAITING_FOR_PLAYERS"
            print(f"[SERVER] Player {sender_id} connected. Sending LOBBY_WAIT.")
            send_framed_message(session.sock, {"message_type": "LOBBY_WAIT"})
        elif len(self.client_sessions) == 2:
            print("[SERVER] Both players connected! Transitioning WAITING_FOR_PLAYERS -> GAME_START.")
            self._initiate_game_start()

    def _initiate_game_start(self) -> None:
        """Transitions FSM to GAME_START, assigns roles, resets board, and notifies players."""
        self.fsm_state = "GAME_START"
        self.board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.active_player = self.starting_player

        # Send GAME_START with assigned player number to each client
        for pid, sess in self.client_sessions.items():
            send_framed_message(
                sess.sock,
                {
                    "message_type": "GAME_START",
                    "player_number": pid,
                },
            )

        # Transition to PLAYER_TURN and broadcast initial STATE_UPDATE
        self.fsm_state = "PLAYER_TURN"
        print(f"[SERVER] FSM -> PLAYER_TURN. Active turn: Player {self.active_player}.")
        self._broadcast_state_update()

    def _handle_move(self, session: ClientSession, msg: dict) -> None:
        """Validates and processes an active player's MOVE request."""
        sender_id = session.player_id

        # 1. State check
        if self.fsm_state != "PLAYER_TURN":
            send_framed_message(
                session.sock,
                {
                    "message_type": "ERROR",
                    "error_message": f"Server not accepting moves in state '{self.fsm_state}'.",
                },
            )
            return

        # 2. Turn Enforcement: Verify sender is the active player
        if sender_id != self.active_player:
            print(f"[SERVER WARNING] Out-of-turn MOVE from Player {sender_id} rejected.")
            send_framed_message(
                session.sock,
                {
                    "message_type": "ERROR",
                    "error_message": f"Out of turn move rejected. It is Player {self.active_player}'s turn.",
                },
            )
            return

        # 3. Payload Validation: Ensure column_number exists and is integer
        col_input = msg.get("column_number")
        if not isinstance(col_input, int):
            send_framed_message(
                session.sock,
                {
                    "message_type": "ERROR",
                    "error_message": "Invalid move payload: 'column_number' must be an integer.",
                },
            )
            return

        # 4. Column Boundary Verification: 1 <= col <= 7
        if not (1 <= col_input <= BOARD_COLS):
            send_framed_message(
                session.sock,
                {
                    "message_type": "ERROR",
                    "error_message": f"Invalid column number {col_input}. Must be between 1 and {BOARD_COLS}.",
                },
            )
            return

        col_idx = col_input - 1

        # 5. Column Capacity Verification: Check if top cell is occupied
        if self.board[0][col_idx] != 0:
            print(f"[SERVER] Move rejected for Player {sender_id}: Column {col_input} is full.")
            send_framed_message(
                session.sock,
                {
                    "message_type": "ERROR",
                    "error_message": "Your move's selected column is full.",
                },
            )
            return

        # 6. Apply Move via Gravity Drop
        self.fsm_state = "EVALUATE_MOVE"
        row_placed = drop_piece(self.board, col_idx, sender_id)
        print(
            f"[SERVER] Player {sender_id} placed chip in Col {col_input} (Row {row_placed + 1})."
        )

        # 7. Evaluate Win / Draw / Turn Toggle
        winner = check_winner(self.board)
        draw = is_board_full(self.board) if winner == 0 else False

        if winner != 0:
            self._handle_round_over(winner_id=winner)
        elif draw:
            self._handle_round_over(winner_id=0)  # 0 indicates draw
        else:
            # Switch active turn to other player
            self.active_player = 2 if self.active_player == 1 else 1
            self.fsm_state = "PLAYER_TURN"
            print(f"[SERVER] Turn switched. Active player: Player {self.active_player}.")
            self._broadcast_state_update()

    def _handle_round_over(self, winner_id: int) -> None:
        """Transitions FSM to GAME_OVER, updates scoreboard, and broadcasts outcome."""
        self.fsm_state = "GAME_OVER"
        self.match_scores["rounds_played"] += 1

        if winner_id == 0:
            self.match_scores["draws"] += 1
            print(f"[SERVER] Round {self.match_scores['rounds_played']} ended in a DRAW!")
        else:
            self.match_scores[f"player_{winner_id}_wins"] += 1
            print(
                f"[SERVER] Player {winner_id} WINS Round {self.match_scores['rounds_played']}!"
            )

        game_over_payload = {
            "message_type": "GAME_OVER",
            "final_game_outcome": winner_id,
            "scores": dict(self.match_scores),
        }
        self._broadcast(game_over_payload)

        # FSM CLEANUP: Prepare for next round without severing TCP connections
        self.fsm_state = "CLEANUP"
        self.board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
        # Alternate starting player for next round
        self.starting_player = 2 if self.starting_player == 1 else 1
        self.active_player = self.starting_player

        # If both clients remain connected, launch next round automatically
        if len(self.client_sessions) == 2:
            self.fsm_state = "PLAYER_TURN"
            print(
                f"[SERVER] Starting Round {self.match_scores['rounds_played'] + 1}. Active player: Player {self.active_player}."
            )
            self._broadcast_state_update()
        else:
            self.fsm_state = "WAITING_FOR_PLAYERS"

    def _handle_client_disconnect(self, session: ClientSession, abrupt: bool) -> None:
        """Handles client disconnection, socket cleanup, and forfeit win award."""
        disc_id = session.player_id
        other_id = 2 if disc_id == 1 else 1

        print(
            f"[SERVER] Cleaning up session for Player {disc_id} (Abrupt: {abrupt})."
        )

        try:
            self.selector.unregister(session.sock)
        except (KeyError, ValueError):
            pass

        try:
            session.sock.close()
        except OSError:
            pass

        if disc_id in self.client_sessions:
            del self.client_sessions[disc_id]

        # If game was in progress, award victory by forfeit to remaining player and tear down
        if self.fsm_state in ["GAME_START", "PLAYER_TURN", "EVALUATE_MOVE"]:
            if other_id in self.client_sessions:
                other_sess = self.client_sessions[other_id]
                print(
                    f"[SERVER] Player {other_id} awarded victory by forfeit due to Player {disc_id} disconnect."
                )
                self.match_scores["rounds_played"] += 1
                self.match_scores[f"player_{other_id}_wins"] += 1
                send_framed_message(
                    other_sess.sock,
                    {
                        "message_type": "GAME_OVER",
                        "final_game_outcome": other_id,
                        "scores": dict(self.match_scores),
                    },
                )
                # Close remaining client socket per Protocol Blueprint Section 3.1
                try:
                    self.selector.unregister(other_sess.sock)
                except Exception:
                    pass
                try:
                    other_sess.sock.close()
                except Exception:
                    pass
                del self.client_sessions[other_id]

        # Reset board and transition back to WAITING_FOR_PLAYERS
        self.board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.fsm_state = "WAITING_FOR_PLAYERS"
        print(f"[SERVER] FSM reset to '{self.fsm_state}'. Waiting for opponent.")

    def _broadcast_state_update(self) -> None:
        """Broadcasts current board state and active player turn to all connected clients."""
        payload = {
            "message_type": "STATE_UPDATE",
            "board": self.board,
            "active_player": self.active_player,
        }
        self._broadcast(payload)

    def _broadcast(self, payload: dict) -> None:
        """Transmits a framed message to all registered client sessions."""
        stale_clients = []
        for pid, session in list(self.client_sessions.items()):
            success = send_framed_message(session.sock, payload)
            if not success:
                stale_clients.append(session)

        for session in stale_clients:
            print(f"[SERVER] Broadcast failed to Player {session.player_id}. Tearing down.")
            self._handle_client_disconnect(session, abrupt=True)

    def _cleanup_all(self) -> None:
        """Tears down all active sockets and selector registrations upon server exit."""
        print("[SERVER] Closing all client sockets and server listening port...")
        for session in list(self.client_sessions.values()):
            try:
                self.selector.unregister(session.sock)
            except Exception:
                pass
            try:
                session.sock.close()
            except Exception:
                pass
        self.client_sessions.clear()

        if self.server_sock:
            try:
                self.selector.unregister(self.server_sock)
            except Exception:
                pass
            try:
                self.server_sock.close()
            except Exception:
                pass

        try:
            self.selector.close()
        except Exception:
            pass
        print("[SERVER] Cleanup complete. Server terminated cleanly.")


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments according to Sprint 3 specifications."""
    parser = CustomArgumentParser(
        description="Connect Four Authoritative Game Server (CS 457 Sprint 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example Usage:\n"
            "  python3 server.py -p 4570\n"
            "  python3 server.py -p 8080\n"
        ),
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        required=True,
        help="Listening port number (required, valid range: 1024-65535)",
    )
    args = parser.parse_args()
    validate_port(args.port)
    return args


def main() -> None:
    args = parse_arguments()
    server = ConnectFourServer(host="0.0.0.0", port=args.port)
    server.start()


if __name__ == "__main__":
    main()
