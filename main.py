import asyncio
import os

from pyrogram import idle

from app import app, call_py, log
from utils.cover import ensure_cover

# Register handlers
from modules import play, song  # noqa: F401


async def _healthcheck_server():
    """
    Railway treats services as 'web' by default and sends SIGTERM if nothing
    is listening on $PORT (healthcheck failure -> restart loop). We bind a
    tiny TCP server that answers HTTP 200 'ok' so Railway keeps us alive.
    No extra dependencies needed.
    """
    port_env = os.environ.get("PORT")
    if not port_env:
        return None
    try:
        port = int(port_env)
    except ValueError:
        return None

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            try:
                await asyncio.wait_for(reader.read(2048), timeout=2.0)
            except Exception:  # noqa: BLE001
                pass
            body = b"ok"
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            writer.write(response)
            await writer.drain()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

    server = await asyncio.start_server(handle, "0.0.0.0", port)
    log.info("Healthcheck HTTP server listening on 0.0.0.0:%s", port)
    asyncio.create_task(server.serve_forever())
    return server


async def _startup():
    # Ensure cover image exists before any .song request
    ensure_cover()

    # Start healthcheck server FIRST so Railway sees the port immediately
    await _healthcheck_server()

    await app.start()
    await call_py.start()

    me = await app.get_me()
    log.info("Userbot started as @%s (id=%s)", me.username, me.id)


async def _main():
    await _startup()
    try:
        await idle()
    finally:
        try:
            await app.stop()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    # Make sure working dir is the script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    asyncio.run(_main())
