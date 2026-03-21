"""
DUT (Device Under Test) model layer.

Provides DUTConfig — a structured, board-first representation of a DUT,
replacing direct raw-dict access to board YAML configs.
"""

from ael.dut.model import DUTConfig, ProcessorConfig
from ael.dut.loader import load_dut
from ael.dut.registry import load_dut_from_file

__all__ = ["DUTConfig", "ProcessorConfig", "load_dut", "load_dut_from_file"]
