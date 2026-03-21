"""
DUTProvider — structural protocol for objects that provide DUT configuration.

Any object implementing these methods is a valid DUT provider.
Concrete implementations: DUTConfig (ael.dut.model).
"""

from __future__ import annotations

from typing import Any, Dict, List, runtime_checkable

try:
    from typing import Protocol
except ImportError:  # Python < 3.8
    from typing_extensions import Protocol  # type: ignore


@runtime_checkable
class DUTProvider(Protocol):
    """
    Structural protocol for DUT configuration providers.

    An object satisfies DUTProvider if it exposes:
    - board_id: str
    - name: str
    - mcu: str             (primary processor id)
    - target: str          (alias of mcu)
    - processors: list     (list of ProcessorConfig)
    - to_legacy_dict()     (returns flat dict compatible with legacy callers)

    This protocol allows connection_model, strategy_resolver, and pipeline
    to accept DUTConfig without importing it directly, keeping CORE boundaries
    intact.
    """

    @property
    def board_id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def mcu(self) -> str: ...

    @property
    def target(self) -> str: ...

    @property
    def processors(self) -> List[Any]: ...

    def to_legacy_dict(self) -> Dict[str, Any]: ...
