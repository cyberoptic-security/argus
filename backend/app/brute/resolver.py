import asyncio
import contextlib
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

DEFAULT_RESOLVERS = ["8.8.8.8", "1.1.1.1"]
DEFAULT_CONCURRENCY = 100


async def bruteforce(
    domain: str,
    words: list[str],
    resolvers: list[str] | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> AsyncIterator[tuple[str, list[str]]]:
    """Yield (fqdn, [ip, ...]) for each word that resolves via A record."""
    import aiodns

    resolvers = resolvers or DEFAULT_RESOLVERS
    semaphore = asyncio.Semaphore(concurrency)
    queue: asyncio.Queue[tuple[str, list[str]] | None] = asyncio.Queue()

    async def resolve_word(word: str, resolver: aiodns.DNSResolver) -> None:
        fqdn = f"{word}.{domain}"
        async with semaphore:
            try:
                result = await resolver.query(fqdn, "A")
                ips = [r.host for r in result]
                if ips:
                    await queue.put((fqdn, ips))
                    logger.debug("brute: %s -> %s", fqdn, ips)
            except aiodns.error.DNSError:
                pass
            except Exception as e:
                logger.debug("brute: resolve error for %s: %s", fqdn, e)

    async def runner() -> None:
        resolver = aiodns.DNSResolver(nameservers=resolvers)
        tasks = [asyncio.create_task(resolve_word(w, resolver)) for w in words]
        await asyncio.gather(*tasks)
        await queue.put(None)

    runner_task = asyncio.create_task(runner())
    logger.info("brute: starting %d word lookups against %s (concurrency=%d)", len(words), domain, concurrency)

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        runner_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner_task
