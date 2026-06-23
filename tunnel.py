import asyncio
import logging
import re
from pathlib import Path

_logger = logging.getLogger(__name__)

TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
DEFAULT_CLOUDFLARED_PATH = Path(r"C:\Users\antpl\Downloads\cloudflared-windows-amd64.exe")

_tunnel_url: str | None = None
_process: asyncio.subprocess.Process | None = None
_tunnel_url_event = asyncio.Event()
_stop_event = asyncio.Event()


def get_tunnel_url() -> str | None:
    return _tunnel_url


async def wait_for_url(timeout: float = 60.0) -> str:
    url = get_tunnel_url()
    if url:
        return url
    await asyncio.wait_for(_tunnel_url_event.wait(), timeout=timeout)
    url = get_tunnel_url()
    if url is None:
        raise RuntimeError("Tunnel URL event is set but URL is missing")
    return url


async def _read_stream(stream: asyncio.StreamReader | None, tag: str):
    if stream is None:
        return
    while True:
        try:
            line = await stream.readline()
        except Exception as exc:
            _logger.debug("%s stream read error: %s", tag, exc)
            return
        if not line:
            return
        text = line.decode("utf-8", errors="replace").rstrip()
        _logger.debug("[%s] %s", tag, text)
        match = TUNNEL_RE.search(text)
        if match:
            global _tunnel_url
            _tunnel_url = match.group(0)
            _tunnel_url_event.set()
            _logger.info("Cloudflare tunnel URL: %s", _tunnel_url)


async def _kill_process():
    global _process
    process = _process
    if process is None:
        return
    try:
        process.terminate()
        await asyncio.wait_for(process.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
    except ProcessLookupError:
        pass
    _process = None


async def _launch_tunnel(
    local_url: str,
    cloudflared_path: Path,
    startup_timeout: float,
) -> None:
    global _process, _tunnel_url

    await _kill_process()
    _tunnel_url = None
    _tunnel_url_event.clear()

    cmd = [str(cloudflared_path), "tunnel", "--url", local_url]
    _logger.info("Starting cloudflared: %s", " ".join(cmd))
    try:
        _process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to start cloudflared: {exc}") from exc

    stdout_task = asyncio.create_task(_read_stream(_process.stdout, "stdout"))
    stderr_task = asyncio.create_task(_read_stream(_process.stderr, "stderr"))
    found_task = asyncio.create_task(_tunnel_url_event.wait())
    stop_task = asyncio.create_task(_stop_event.wait())

    done, pending = await asyncio.wait(
        [found_task, stop_task],
        return_when=asyncio.FIRST_COMPLETED,
        timeout=startup_timeout,
    )

    for task in pending:
        task.cancel()
    for task in done:
        task.exception()

    if _stop_event.is_set():
        await _kill_process()
        raise asyncio.CancelledError()

    if not _tunnel_url_event.is_set():
        await _kill_process()
        stdout_task.cancel()
        stderr_task.cancel()
        raise RuntimeError("Timed out waiting for cloudflared tunnel URL")


async def _watch_process():
    process = _process
    if process is None:
        return
    await process.wait()


async def maintain_tunnel(
    local_url: str = "http://localhost:8080",
    cloudflared_path: Path | str = DEFAULT_CLOUDFLARED_PATH,
    startup_timeout: float = 60.0,
    restart_delay: float = 3.0,
):
    global _tunnel_url
    cloudflared_path = Path(cloudflared_path)

    while not _stop_event.is_set():
        try:
            await _launch_tunnel(local_url, cloudflared_path, startup_timeout)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _logger.error("cloudflared launch failed: %s", exc)
            _tunnel_url = None
            _tunnel_url_event.clear()
            try:
                await asyncio.wait_for(_stop_event.wait(), timeout=restart_delay)
            except asyncio.TimeoutError:
                continue
            break

        _logger.info("cloudflared tunnel is running: %s", _tunnel_url)
        await _watch_process()
        _logger.warning("cloudflared process exited; restarting in %ss", restart_delay)
        _tunnel_url = None
        _tunnel_url_event.clear()
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=restart_delay)
        except asyncio.TimeoutError:
            continue
        break


async def start_tunnel(
    local_url: str = "http://localhost:8080",
    cloudflared_path: Path | str = DEFAULT_CLOUDFLARED_PATH,
    startup_timeout: float = 60.0,
) -> str:
    asyncio.create_task(maintain_tunnel(local_url, cloudflared_path, startup_timeout))
    return await wait_for_url(startup_timeout)


async def stop_tunnel():
    _stop_event.set()
    await _kill_process()
