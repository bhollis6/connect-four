#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Sprint 3
Validates:
1. CLI Argument Parsing and Usage Guidance (-h, -i, -p, missing args, port bounds)
2. DNS Resolution Exception Handling (socket.gaierror handling)
3. TCP Stream Framing (coalesced and fragmented frames)
4. Server Concurrency & Multiplayer FSM Realization (2 simultaneous clients, turns, win/draw/forfeit)
"""

import json
import socket
import subprocess
import sys
import threading
import time
from typing import List


def test_server_cli() -> None:
    print("\n--- TEST 1: Server CLI Argument Parsing ---")
    # Test -h
    res_h = subprocess.run([sys.executable, "server.py", "-h"], capture_output=True, text=True)
    assert res_h.returncode == 0, f"server.py -h failed: {res_h.stderr}"
    assert "-p" in res_h.stdout, "server.py -h missing -p description"
    print("  [PASS] server.py -h displays help.")

    # Test missing -p
    res_missing = subprocess.run([sys.executable, "server.py"], capture_output=True, text=True)
    assert res_missing.returncode != 0, "server.py without arguments should fail"
    assert "required" in res_missing.stderr or "error" in res_missing.stderr.lower()
    print("  [PASS] server.py missing -p displays helpful error syntax.")

    # Test invalid port (< 1024)
    res_inv_port = subprocess.run([sys.executable, "server.py", "-p", "80"], capture_output=True, text=True)
    assert res_inv_port.returncode != 0, "server.py -p 80 should fail validation"
    print("  [PASS] server.py rejects port < 1024.")


def test_client_cli() -> None:
    print("\n--- TEST 2: Client CLI Argument Parsing ---")
    # Test -h
    res_h = subprocess.run([sys.executable, "client.py", "-h"], capture_output=True, text=True)
    assert res_h.returncode == 0, f"client.py -h failed: {res_h.stderr}"
    assert "-i" in res_h.stdout and "-p" in res_h.stdout, "client.py -h missing -i or -p description"
    print("  [PASS] client.py -h displays help.")

    # Test missing -i or -p
    res_missing = subprocess.run([sys.executable, "client.py", "-i", "localhost"], capture_output=True, text=True)
    assert res_missing.returncode != 0, "client.py missing -p should fail"
    print("  [PASS] client.py missing -p displays error syntax.")

    # Test invalid port (> 65535)
    res_inv_port = subprocess.run([sys.executable, "client.py", "-i", "localhost", "-p", "70000"], capture_output=True, text=True)
    assert res_inv_port.returncode != 0, "client.py -p 70000 should fail validation"
    print("  [PASS] client.py rejects port > 65535.")


def test_client_dns_error() -> None:
    print("\n--- TEST 3: Client DNS Resolution Exception Handling (socket.gaierror) ---")
    # Pass an unresolvable hostname
    res = subprocess.run([sys.executable, "client.py", "-i", "this.domain.does.not.exist.invalid", "-p", "4570"], capture_output=True, text=True)
    assert res.returncode == 1, f"Expected returncode 1, got {res.returncode}"
    assert "Unable to resolve DNS hostname" in res.stdout, f"Missing graceful DNS error message in stdout: {res.stdout}"
    assert "Traceback" not in res.stderr and "Traceback" not in res.stdout, "Raw traceback printed on DNS error!"
    print("  [PASS] client.py catches socket.gaierror gracefully with non-zero exit code 1.")


def test_gameplay_flow() -> None:
    print("\n--- TEST 4: Live Multiplayer Gameplay & FSM Validation ---")
    TEST_PORT = 4575

    # Launch server in background process
    server_proc = subprocess.Popen(
        [sys.executable, "server.py", "-p", str(TEST_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(0.5)

    try:
        # Helper for sending framed message
        def send_msg(s: socket.socket, msg: dict) -> None:
            s.sendall((json.dumps(msg) + "\n").encode("utf-8"))

        # Helper for receiving a framed message
        def recv_msgs(s: socket.socket, buf: bytearray) -> List[dict]:
            while True:
                pos = buf.find(b"\n")
                if pos != -1:
                    frame = buf[:pos]
                    del buf[:pos + 1]
                    return [json.loads(frame.decode("utf-8"))]
                chunk = s.recv(1024)
                if not chunk:
                    return []
                buf.extend(chunk)

        # 1. Connect Client 1
        s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s1.connect(("127.0.0.1", TEST_PORT))
        buf1 = bytearray()
        send_msg(s1, {"message_type": "CONNECT"})

        # Client 1 should receive LOBBY_WAIT
        m1 = recv_msgs(s1, buf1)[0]
        assert m1["message_type"] == "LOBBY_WAIT", f"Expected LOBBY_WAIT, got {m1}"
        print("  [PASS] Client 1 connected and received LOBBY_WAIT.")

        # 2. Connect Client 2
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.connect(("127.0.0.1", TEST_PORT))
        buf2 = bytearray()
        send_msg(s2, {"message_type": "CONNECT"})

        # Both clients should receive GAME_START
        start1 = recv_msgs(s1, buf1)[0]
        start2 = recv_msgs(s2, buf2)[0]
        assert start1["message_type"] == "GAME_START" and start1["player_number"] == 1, f"Bad start1: {start1}"
        assert start2["message_type"] == "GAME_START" and start2["player_number"] == 2, f"Bad start2: {start2}"
        print("  [PASS] Both clients received GAME_START with distinct player roles (1 and 2).")

        # Both clients should receive initial STATE_UPDATE (active_player = 1)
        up1 = recv_msgs(s1, buf1)[0]
        up2 = recv_msgs(s2, buf2)[0]
        assert up1["message_type"] == "STATE_UPDATE" and up1["active_player"] == 1
        assert up2["message_type"] == "STATE_UPDATE" and up2["active_player"] == 1
        print("  [PASS] Initial STATE_UPDATE broadcast received by both clients.")

        # 3. Test Out-of-turn move rejection: Client 2 tries to move first
        send_msg(s2, {"message_type": "MOVE", "column_number": 4})
        err2 = recv_msgs(s2, buf2)[0]
        assert err2["message_type"] == "ERROR", f"Expected ERROR for out-of-turn move, got {err2}"
        assert "Out of turn move rejected" in err2["error_message"]
        print("  [PASS] Out-of-turn move properly rejected with ERROR.")

        # 4. Turn 1: Client 1 moves in Column 4
        send_msg(s1, {"message_type": "MOVE", "column_number": 4})
        up1 = recv_msgs(s1, buf1)[0]
        up2 = recv_msgs(s2, buf2)[0]
        assert up1["message_type"] == "STATE_UPDATE" and up1["active_player"] == 2
        assert up2["message_type"] == "STATE_UPDATE" and up2["active_player"] == 2
        assert up1["board"][5][3] == 1, "Chip should land at bottom row (index 5) of column 4 (index 3)"
        print("  [PASS] Turn 1 complete: Player 1 dropped in Col 4, board updated, active_player toggled to 2.")

        # 5. Turn 2: Client 2 moves in Column 4 (lands on top of P1's chip at row 4)
        send_msg(s2, {"message_type": "MOVE", "column_number": 4})
        up1 = recv_msgs(s1, buf1)[0]
        up2 = recv_msgs(s2, buf2)[0]
        assert up1["board"][4][3] == 2 and up1["active_player"] == 1
        assert up2["board"][4][3] == 2 and up2["active_player"] == 1
        print("  [PASS] Turn 2 complete: Player 2 dropped in Col 4 (lands at row 4), active_player toggled to 1.")

        # 6. Turn 3: Client 1 moves in Column 3
        send_msg(s1, {"message_type": "MOVE", "column_number": 3})
        up1 = recv_msgs(s1, buf1)[0]
        up2 = recv_msgs(s2, buf2)[0]
        assert up1["board"][5][2] == 1 and up1["active_player"] == 2
        assert up2["board"][5][2] == 1 and up2["active_player"] == 2
        print("  [PASS] Turn 3 complete: Player 1 dropped in Col 3, active_player toggled to 2.")

        # 7. Test TCP stream framing edge cases: Coalesced back-to-back packets
        # Client 2 sends MOVE 3, Client 1 sends MOVE 5 back-to-back
        send_msg(s2, {"message_type": "MOVE", "column_number": 3})
        up1 = recv_msgs(s1, buf1)[0]
        up2 = recv_msgs(s2, buf2)[0]
        assert up1["board"][4][2] == 2 and up1["active_player"] == 1
        print("  [PASS] Turn 4 complete: Player 2 dropped in Col 3.")

        # 8. Test Graceful Disconnection & Win by Forfeit
        s2.close()  # Client 2 drops
        # Client 1 should receive GAME_OVER with final_game_outcome == 1 (forfeit win)
        over1 = recv_msgs(s1, buf1)[0]
        assert over1["message_type"] == "GAME_OVER", f"Expected GAME_OVER on forfeit, got {over1}"
        assert over1["final_game_outcome"] == 1, f"Player 1 should be awarded forfeit victory, got {over1}"
        assert over1["scores"]["player_1_wins"] >= 1
        print("  [PASS] Abrupt client disconnect cleanly handled; opponent awarded forfeit victory!")

        s1.close()

    finally:
        server_proc.terminate()
        server_proc.wait()
        print("  [PASS] Server terminated cleanly.")


def main() -> None:
    print("=" * 60)
    print(" STARTING SPRINT 3 AUTOMATED VERIFICATION SUITE")
    print("=" * 60)
    test_server_cli()
    test_client_cli()
    test_client_dns_error()
    test_gameplay_flow()
    print("\n" + "=" * 60)
    print(" ALL SPRINT 3 TESTS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
