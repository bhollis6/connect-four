# How AI Was Used in This Project

## Sprints 0, 1 & 2: Architectural Design & Verification
* **Markdown & Diagram Generation:** AI was used to draft initial boilerplate Markdown documents and Mermaid state/sequence diagram syntax based on the assignment rubrics.
* **Rubric Verification:** AI assisted in auditing proposed schemas and FSM transitions against course requirements to ensure no critical socket behaviors (such as TCP 0-byte EOF detection or exception handling) were omitted.

## Sprint 3: Socket Implementation & Automated Testing
* **Constrained Code Drafting:** Prompted AI assistants using strict design constraints (as detailed in `ai_prompts.md`) to implement the `selectors`-based non-blocking event loop in `server.py` and the interactive CLI client in `client.py`.
* **DNS Resolution Error Handling:** Leveraged AI guidance to implement the mandatory `try...except socket.gaierror` pattern specified in the Sprint 3 assignment.
* **Automated Test Harness:** Used AI to generate an automated socket test suite (`test_connect_four.py`) that executes live multi-turn tests over localhost.
* **Debugging & Refinement:** Identified and resolved a Windows console encoding limitation with Unicode characters by replacing them with clean ASCII banners.

All generated code was thoroughly reviewed, tested, and validated against the custom protocol blueprint and FSM specifications.
