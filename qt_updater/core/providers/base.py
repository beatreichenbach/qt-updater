from abc import ABC, abstractmethod

from ..release import Release


class ReleaseProvider(ABC):
    @abstractmethod
    def latest(self) -> Release | None: ...
