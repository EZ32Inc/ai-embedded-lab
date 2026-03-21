"""
DUT interfaces — structural protocols for DUT providers.

Mirrors the pattern established in ael/instruments/interfaces/:
concrete implementations are not imported here; callers depend on the
protocol, not the implementation.
"""

from ael.dut.interfaces.provider import DUTProvider

__all__ = ["DUTProvider"]
