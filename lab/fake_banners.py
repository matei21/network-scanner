"""Fake service banners for the hotspot lab (Setup C).

  port 2323 -> looks like BusyBox telnetd   => TELNET_OPEN
  port 2121 -> looks like vsftpd 2.3.4      => FTP_CLEARTEXT + OUTDATED_SERVICE
  port 2222 -> looks like OpenSSH 8.9p1     => SSH_OPEN (info, 0 points)

Golden rule: simulate, do not expose. These listeners only send text.
Nothing is executed, no files exist, every login attempt is refused.

Run:  python fake_banners.py            (inside Docker this is automatic)
Env:  BANNER_HOST (default 0.0.0.0), TELNET_PORT (2323), FTP_PORT (2121),
      SSH_PORT (2222). Set a port to 0 to turn that fake service off
      (e.g. TELNET_PORT=0 if you already run another fake telnet).
"""

from __future__ import annotations

import asyncio
import os

HOST = os.environ.get("BANNER_HOST", "0.0.0.0")
TELNET_PORT = int(os.environ.get("TELNET_PORT", "2323"))
FTP_PORT = int(os.environ.get("FTP_PORT", "2121"))
SSH_PORT = int(os.environ.get("SSH_PORT", "2222"))

IDLE_TIMEOUT = 15      # seconds before an idle client is dropped
MAX_LINES = 10         # max commands per connection
MAX_LINE_BYTES = 256   # ignore anything longer

# Telnet option negotiation (IAC DO ECHO, IAC DO NAWS, IAC WILL ECHO,
# IAC WILL SUPPRESS-GO-AHEAD) - what a BusyBox telnetd sends first.
TELNET_NEGOTIATION = b"\xff\xfd\x01\xff\xfd\x1f\xff\xfb\x01\xff\xfb\x03"


async def _readline(reader: asyncio.StreamReader) -> bytes | None:
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=IDLE_TIMEOUT)
    except (asyncio.TimeoutError, ConnectionError, ValueError):
        return None
    if not line:
        return None
    return line[:MAX_LINE_BYTES]


async def _close(writer: asyncio.StreamWriter) -> None:
    try:
        writer.close()
        await writer.wait_closed()
    except ConnectionError:
        pass


async def handle_telnet(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        writer.write(TELNET_NEGOTIATION + b"\r\nlab-iot login: ")
        await writer.drain()
        for _ in range(MAX_LINES):
            if await _readline(reader) is None:
                break
            writer.write(b"\r\nLogin incorrect\r\nlab-iot login: ")
            await writer.drain()
    except ConnectionError:
        pass
    finally:
        await _close(writer)


async def handle_ftp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        writer.write(b"220 (vsFTPd 2.3.4)\r\n")
        await writer.drain()
        for _ in range(MAX_LINES):
            line = await _readline(reader)
            if line is None:
                break
            cmd = line.strip().split(b" ", 1)[0].upper()
            if cmd == b"USER":
                reply = b"331 Please specify the password.\r\n"
            elif cmd == b"QUIT":
                writer.write(b"221 Goodbye.\r\n")
                await writer.drain()
                break
            elif cmd == b"PASS":
                reply = b"530 Login incorrect.\r\n"
            else:
                reply = b"530 Please login with USER and PASS.\r\n"
            writer.write(reply)
            await writer.drain()
    except ConnectionError:
        pass
    finally:
        await _close(writer)


async def handle_ssh(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Send an OpenSSH version line, read the client's line, then hang up.
    No key exchange happens, so nobody can ever log in."""
    try:
        writer.write(b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6\r\n")
        await writer.drain()
        await _readline(reader)
    except ConnectionError:
        pass
    finally:
        await _close(writer)


async def main() -> None:
    services = [
        ("fake telnet", handle_telnet, TELNET_PORT),
        ("fake ftp", handle_ftp, FTP_PORT),
        ("fake ssh", handle_ssh, SSH_PORT),
    ]
    servers = []
    for name, handler, port in services:
        if port == 0:
            print(f"{name}: off")
            continue
        servers.append(await asyncio.start_server(handler, HOST, port))
        print(f"{name} on {HOST}:{port}")
    if not servers:
        print("all fake services are off")
        return
    await asyncio.gather(*(s.serve_forever() for s in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
