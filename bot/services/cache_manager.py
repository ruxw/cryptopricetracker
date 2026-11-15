import io
import time
import asyncio
from typing import Dict, Tuple, Any, Callable, Optional

# In-memory LRU/TTL render cache: cache_key -> (expiry_timestamp, bytes_data)
_RENDER_CACHE: Dict[str, Tuple[float, bytes]] = {}
_IN_FLIGHT_TASKS: Dict[str, asyncio.Future] = {}
_CACHE_LOCK = asyncio.Lock()
DEFAULT_RENDER_TTL = 15.0  # seconds

def _make_key(func_name: str, *args) -> str:
    """Generate deterministic string key from function arguments."""
    normalized = []
    for a in args:
        if isinstance(a, float):
            normalized.append(f"{a:.4f}")
        elif isinstance(a, list):
            # Sample list to avoid hashing huge arrays
            normalized.append(f"len_{len(a)}_{a[0] if a else 0}_{a[-1] if a else 0}")
        else:
            normalized.append(str(a))
    return f"{func_name}:" + ":".join(normalized)

async def get_cached_or_render(
    render_func: Callable[..., io.BytesIO],
    *args,
    ttl: float = DEFAULT_RENDER_TTL
) -> io.BytesIO:
    """
    Ultra-fast cached async renderer with Single-Flight Coalescing:
    - If cached bytes exist within TTL, returns instant BytesIO (<1ms)
    - If multiple requests for the same card arrive simultaneously (e.g. 50+ users calling /btc or /top),
      only ONE thread renders it while the other 49 wait on the same Future, avoiding CPU starvation
    - Offloads CPU-heavy PIL rasterization to worker threads via asyncio.to_thread
    - Zero event-loop blocking, perfectly handling 50+ concurrent requests
    """
    key = _make_key(render_func.__name__, *args)
    now = time.time()

    loop = asyncio.get_running_loop()
    leader_future: Optional[asyncio.Future] = None

    async with _CACHE_LOCK:
        # 1. Cache hit check
        if key in _RENDER_CACHE:
            expiry, data = _RENDER_CACHE[key]
            if now < expiry:
                buf = io.BytesIO(data)
                buf.seek(0)
                return buf
            else:
                del _RENDER_CACHE[key]

        # 2. In-flight single-flight coalescing check
        if key in _IN_FLIGHT_TASKS:
            existing_future = _IN_FLIGHT_TASKS[key]
        else:
            leader_future = loop.create_future()
            _IN_FLIGHT_TASKS[key] = leader_future
            existing_future = None

    # If another coroutine is already rendering this exact card, await its result
    if existing_future is not None:
        data = await existing_future
        buf = io.BytesIO(data)
        buf.seek(0)
        return buf

    # We are the designated worker for this card
    try:
        buf = await asyncio.to_thread(render_func, *args)
        data = buf.getvalue()

        async with _CACHE_LOCK:
            # Prune expired entries if cache grows
            if len(_RENDER_CACHE) > 150:
                expired = [k for k, (exp, _) in _RENDER_CACHE.items() if time.time() >= exp]
                for k in expired:
                    del _RENDER_CACHE[k]

            _RENDER_CACHE[key] = (time.time() + ttl, data)
            _IN_FLIGHT_TASKS.pop(key, None)

        if leader_future and not leader_future.done():
            leader_future.set_result(data)

    except Exception as exc:
        async with _CACHE_LOCK:
            _IN_FLIGHT_TASKS.pop(key, None)
        if leader_future and not leader_future.done():
            leader_future.set_exception(exc)
        raise exc

    out_buf = io.BytesIO(data)
    out_buf.seek(0)
    return out_buf
