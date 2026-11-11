#!/usr/bin/env python3
"""
Connect Four Network Game Client (CS 457 Sprint 3)

Author: Braden Hollis
Course: CS 457 - Computer Networks
Environment: Python 3.x (Compatible with CML Linux nodes and local developer machines)

Architectural Overview:
- Transport Layer: TCP stream sockets (AF_INET, SOCK_STREAM)
- Framing: Newline-delimited ('\\n') JSON payloads (UTF-8 encoded)
- DNS Resolution: Resolves hostname via socket.gethostbyname() with graceful exception handling
- Protocol Adherence: Matches Sprint 1 protocol blueprint & FSM (CONNECT, LOBBY_WAIT, GAME_START, MOVE, STATE_UPDATE, ERROR, DISCONNECT, GAME_OVER)
- User Interface: Interactive CLI with human-readable board matrix, turn indicators, and live scoreboard
"""

import argparse
import functools
import json
import socket
import sys
from typing import List, Optional, Tuple

# Ensure all prints are unbuffered for immediate CLI display
print = functools.partial(print, flush=True)

BOARD_ROWS = 6
BOARD_COLS = 7


class CustomArgumentParser(argparse.ArgumentParser):
    """Argument parser that prints full help usage on missing/malformed arguments."""

    def error(self, message: str) -> None:
        sys.stderr.write(f"\n[ERROR] {message}\n\n")
        self.print_help(sys.stderr)
        sys.exit(2)


def validate_port(port_str: str) -> int:
    """Validates that the specified port is an integer within the unprivileged range (1024-65535)."""
    try:
        port_val = int(port_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid port '{port_str}'. Port must be an integer.")
    if not (1024 <= port_val <= 65535):
        raise argparse.ArgumentTypeError(
            f"Port {port_val} out of range. Port must be between 1024 and 65535."
        )
    return port_val


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments according to Sprint 3 specifications."""
    parser = CustomArgumentParser(
        description="Connect Four Network CLI Game Client (CS 457 Sprint 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example Usage:\n"
            "  python3 client.py -i localhost -p 4570\n"
            "  python3 client.py -i server.hollis.edu -p 8080\n"
        ),
    )
    parser.add_argument(
        "-i",
        "--hostname",
        type=str,
        required=True,
        help="Server DNS hostname or IP address (e.g., server.hollis.edu, localhost)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=validate_port,
        required=True,
        help="Server port number (required, valid range: 1024-65535)",
    )
    return parser.parse_args()


def resolve_server_address(hostname: str) -> str:
    """
    Resolves DNS hostname to an IPv4 address.
    Fails gracefully with a user-friendly error message if resolution fails.
    """
    try:
        server_ip = socket.gethostbyname(hostname)
        return server_ip
    except socket.gaierror as e:
        print(f"[ERROR] Unable to resolve DNS hostname '{hostname}'.")
        print(
            "Please check your Cisco router DNS configuration ('ip dns server' / 'ip host') or verify domain spelling."
        )
        sys.exit(1)


def send_framed_message(sock: socket.socket, message: dict) -> bool:
    """
    Serializes a dictionary to JSON, appends newline delimiter ('\\n'),
    encodes to UTF-8, and transmits across the TCP stream via sendall().
    """
    try:
        payload = json.dumps(message) + "\n"
        sock.sendall(payload.encode("utf-8"))
        return True
    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
        print(f"\n[CLIENT ERROR] Failed to send message to server: {e}")
        return False


def extract_messages_from_buffer(buffer: bytearray) -> List[dict]:
    """
    Scans the stream buffer for newline delimiters ('\\n').
    Extracts all fully-received JSON messages and removes them from the buffer.
    Incomplete trailing bytes remain in the buffer for future chunks.
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
                print(f"[CLIENT WARNING] Malformed JSON received: {line} ({err})")
    return messages


def render_board(board: List[List[int]]) -> str:
    """
    Formats the 6x7 grid into a clean, human-readable ASCII Connect Four board.
    Symbols: '.' = empty, 'X' = Player 1, 'O' = Player 2.
    """
    symbols = {0: ".", 1: "X", 2: "O"}
    lines = []
    lines.append("\n  +---+---+---+---+---+---+---+")
    for r in range(BOARD_ROWS):
        row_str = (
            "  | "
            + " | ".join(symbols.get(board[r][c], "?") for c in range(BOARD_COLS))
            + " |"
        )
        lines.append(row_str)
        lines.append("  +---+---+---+---+---+---+---+")
    lines.append("    1   2   3   4   5   6   7  \n")
    return "\n".join(lines)


def display_scoreboard(scores: dict) -> None:
    """Prints a formatted match scoreboard summary."""
    print("\n" + "=" * 45)
    print("               CURRENT SCOREBOARD")
    print("=" * 45)
    print(f"  Player 1 (X) Wins: {scores.get('player_1_wins', 0)}")
    print(f"  Player 2 (O) Wins: {scores.get('player_2_wins', 0)}")
    print(f"  Draws:             {scores.get('draws', 0)}")
    print(f"  Total Rounds:      {scores.get('rounds_played', 0)}")
    print("=" * 45 + "\n")


class ConnectFourClient:
    """
    Connect Four Network Game Client.
    Manages socket connection, user inputs, board rendering, and server protocol messages.
    """

    def __init__(self, hostname: str, server_ip: str, port: int) -> None:
        self.hostname = hostname
        self.server_ip = server_ip
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.buffer = bytearray()
        self.player_number: Optional[int] = None
        self.token: Optional[str] = None
        self.is_my_turn = False
        self.running = False

    def start(self) -> None:
        """Connects to server, initiates protocol handshake, and enters client game loop."""
        print("=" * 60)
        print(" Connect Four CLI Game Client")
        print(f" Target Server: {self.hostname} ({self.server_ip}):{self.port}")
        print("=" * 60)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.server_ip, self.port))
            print(f"[CLIENT] Connected to server at {self.server_ip}:{self.port}.")
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            print(
                f"[ERROR] Unable to connect to server at {self.hostname} ({self.server_ip}):{self.port} - {e}"
            )
            sys.exit(1)

        # Transmit Sprint 1 CONNECT request
        send_framed_message(self.sock, {"message_type": "CONNECT"})
        self.running = True

        try:
            self._event_loop()
        except KeyboardInterrupt:
            print("\n[CLIENT] Session interrupted by user (Ctrl+C). Quitting...")
            if self.sock:
                send_framed_message(self.sock, {"message_type": "DISCONNECT"})
        finally:
            self._cleanup()

    def _event_loop(self) -> None:
        """Main client loop: receives TCP chunks, extracts messages, and prompts for moves."""
        while self.running:
            # First process any complete messages already accumulated in the buffer
            messages = extract_messages_from_buffer(self.buffer)
            if not messages:
                try:
                    chunk = self.sock.recv(1024)
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                    print(f"\n[CLIENT] Connection lost to server: {e}")
                    break

                # TCP EOF (0-byte chunk indicates server closed socket)
                if not chunk:
                    print("\n[CLIENT] Server closed the connection (EOF received). Exiting.")
                    break

                self.buffer.extend(chunk)
                messages = extract_messages_from_buffer(self.buffer)

            for msg in messages:
                self._handle_server_message(msg)

    def _handle_server_message(self, msg: dict) -> None:
        """Processes an incoming structured JSON message from the server."""
        msg_type = msg.get("message_type")

        if msg_type == "LOBBY_WAIT":
            print("\n[LOBBY] Waiting in room for Player 2 to connect...")

        elif msg_type == "GAME_START":
            self.player_number = msg.get("player_number")
            self.token = "X" if self.player_number == 1 else "O"
            opponent_token = "O" if self.player_number == 1 else "X"
            opponent_number = 2 if self.player_number == 1 else 1

            print("\n" + "#" * 60)
            print("                 GAME START NOTIFICATION")
            print("#" * 60)
            print(f"  Assigned Role:   Player {self.player_number} (Token: '{self.token}')")
            print(f"  Opponent:        Player {opponent_number} (Token: '{opponent_token}')")
            print("#" * 60)

        elif msg_type == "STATE_UPDATE":
            board = msg.get("board", [])
            active_player = msg.get("active_player", 1)
            self.is_my_turn = active_player == self.player_number

            # Render updated board
            print(render_board(board))

            if self.is_my_turn:
                print(f">>> YOUR TURN! (Player {self.player_number} - '{self.token}')")
                self._prompt_and_send_move()
            else:
                opp_token = "O" if self.player_number == 1 else "X"
                print(
                    f"[*] Waiting for Player {active_player} ('{opp_token}') to make a move..."
                )

        elif msg_type == "ERROR":
            err_msg = msg.get("error_message", "Unknown error occurred.")
            print(f"\n[SERVER ERROR] {err_msg}")
            # If server reported an error on our turn (e.g. column full), re-prompt
            if self.is_my_turn:
                self._prompt_and_send_move()

        elif msg_type == "GAME_OVER":
            outcome = msg.get("final_game_outcome", 0)
            scores = msg.get("scores", {})

            print("\n" + "*" * 60)
            print("                     GAME OVER")
            print("*" * 60)
            if outcome == 0:
                print("  [RESULT] Round ended in a DRAW (Board full)!")
            elif outcome == self.player_number:
                print(f"  [RESULT] VICTORY! You (Player {self.player_number}) won the round!")
            else:
                print(f"  [RESULT] DEFEAT! Player {outcome} won the round.")
            print("*" * 60)

            display_scoreboard(scores)
            print("[*] Waiting for server instructions or next round (press Ctrl+C to exit)...")

        else:
            print(f"[CLIENT WARNING] Received unknown message type: {msg_type}")

    def _prompt_and_send_move(self) -> None:
        """Prompts the user for a column choice (1-7) or 'q' to quit, and transmits the MOVE."""
        while True:
            try:
                user_input = input("Enter column (1-7) or 'q' to quit: ").strip()
            except EOFError:
                user_input = "q"

            if user_input.lower() in ["q", "quit", "exit"]:
                print("[CLIENT] Quitting game...")
                send_framed_message(self.sock, {"message_type": "DISCONNECT"})
                self.running = False
                sys.exit(0)

            if not user_input.isdigit():
                print("[ERROR] Please enter a valid number between 1 and 7 (or 'q' to quit).")
                continue

            col_choice = int(user_input)
            if not (1 <= col_choice <= BOARD_COLS):
                print(
                    f"[ERROR] Column {col_choice} out of range! Must be between 1 and {BOARD_COLS}."
                )
                continue

            # Valid move input
            move_payload = {
                "message_type": "MOVE",
                "column_number": col_choice,
            }
            print(f"[CLIENT] Submitting move for Column {col_choice}...")
            send_framed_message(self.sock, move_payload)
            break

    def _cleanup(self) -> None:
        """Closes the client socket gracefully."""
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        print("[CLIENT] Socket closed. Disconnected.")


def main() -> None:
    args = parse_arguments()
    server_ip = resolve_server_address(args.hostname)
    client = ConnectFourClient(
        hostname=args.hostname, server_ip=server_ip, port=args.port
    )
    client.start()


if __name__ == "__main__":
    main()
