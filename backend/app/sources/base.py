from abc import ABC, abstractmethod
from typing import AsyncIterator


class Source(ABC):
    name: str
    display_name: str
    requires_key: bool = False

    @abstractmethod
    async def run(
        self,
        domain: str,
        api_key: str | None,
        api_secret: str | None,
    ) -> AsyncIterator[str]:
        """Yield discovered FQDNs one at a time."""
