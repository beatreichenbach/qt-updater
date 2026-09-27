from abc import ABC, abstractmethod

from .. import models


class ReleaseProvider(ABC):
    @abstractmethod
    def latest(self) -> models.Release | None: ...
