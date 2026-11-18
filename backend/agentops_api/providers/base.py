from abc import ABC, abstractmethod


class JudgeProvider(ABC):
    @abstractmethod
    async def score(self, prompt: str) -> str:
        raise NotImplementedError
