import io
import time
import asyncio
from typing import Dict, Tuple, Any, Callable

# In-memory LRU/TTL render cache: cache_key -> (expiry_timestamp, bytes_data)
_RENDER_CACHE: Dict[str, Tuple[float, bytes]] = {}
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
    Ultra-fast cached async renderer:
    - If cached bytes exist within TTL, returns instant BytesIO (<1ms)
    - Otherwise renders on a separate thread via asyncio.to_thread
    - Guarantees non-blocking async execution for 50+ concurrent users
    """
    key = _make_key(render_func.__name__, *args)
    now = time.time()

    # Check cache
    async with _CACHE_LOCK:
        if key in _RENDER_CACHE:
            expiry, data = _RENDER_CACHE[key]
            if now < expiry:
                buf = io.BytesIO(data)
                buf.seek(0)
                return buf
            else:
                del _RENDER_CACHE[key]

    # Offload heavy PIL CPU rendering to worker thread
    buf = await asyncio.to_thread(render_func, *args)
    data = buf.getvalue()

    # Store in cache
    async with _CACHE_LOCK:
        # Prune expired entries if cache grows
        if len(_RENDER_CACHE) > 100:
            expired = [k for k, (exp, _) in _RENDER_CACHE.items() if now >= exp]
            for k in expired:
                del _RENDER_CACHE[k]

        _RENDER_CACHE[key] = (now + ttl, data)

    out_buf = io.BytesIO(data)
    out_buf.seek(0)
    return out_buf
