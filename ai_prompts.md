Documented system prompts for AI coding tools to implement serialization function matching the schema.

1. Write a Python function that serializes a dictionary to JSON, encodes it to UTF-8, and appends a `\n` newline delimiter. Then, send it over the socket. Do NOT use generic socket code. Follow the newline-delimited framing rule {give example messages}.

2. Write a python function to read chunks from a TCP socket into a bytearray buffer. Every time a `\n` delimiter is found, take everything between that and the previous `\n`, parse the JSON, and leave incomplete data in the buffer. Break the loop if `recv()` returns `b''`."
