from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional

class BaseBackend(ABC):
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    @abstractmethod
    async def get_models(self) -> List[str]:
        """Return a list of available model IDs."""
        pass

    @abstractmethod
    async def get_loaded_models(self) -> List[Dict]:
        """Return a list of models currently loaded in VRAM/RAM."""
        pass

    @abstractmethod
    async def unload_all(self) -> bool:
        """Eject all loaded models to free up resources."""
        pass

    @abstractmethod
    async def stream_generate(self, model: str, prompt: str) -> AsyncGenerator[Dict, None]:
        """Stream responses from the backend."""
        pass

    @abstractmethod
    def is_compatible(self, chunk: Dict) -> bool:
        """Check if a chunk indicates the end of a stream."""
        pass
