import socket
from typing import Callable, Awaitable



async def start_subscriber(HOST, PORT, process_line: Callable[[str], Awaitable[None]]):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Allow the port to be reused immediately after a crash
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"Listening for Minecraft data on {PORT}...")
        
        while True: # Outer loop: Keep the server alive forever
            try:
                conn, addr = s.accept()
                with conn:
                    print(f"--- Minecraft Server Connected from {addr} ---")
                    buffer = ""
                    while True: # Inner loop: Handle the current stream
                        data = conn.recv(4096).decode('utf-8', errors='ignore')
                        if not data: 
                            print("--- Minecraft Server Disconnected ---")
                            break
                        
                        buffer += data
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            await process_line(line)
            except Exception as e:
                print(f"Connection Error: {e}")
                # Wait a moment before allowing a new connection attempt
                continue

