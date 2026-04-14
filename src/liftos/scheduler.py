from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from liftos.models import Building, Car, Request


class Scheduler(Protocol):
    def assign(self, request: Request, building: Building) -> Car: ...
