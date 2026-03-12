# Shared Instrument Resource Model v0.1

## Purpose

This note preserves the current understanding of shared-instrument ownership in
AEL. It is a design note only. It does not change current runtime claims and is
not a commitment to implement channel-level sharing now.

## Current State

AEL resource ownership is currently modeled mostly at the whole
instrument-instance level.

In practice, runtime ownership and locking are centered around resources such
as:

- instrument instance
- instrument endpoint
- DUT identity
- serial port
- meter endpoint

Current AEL does not yet have a formal runtime model for sub-resources,
channels, or partitions inside one instrument.

## Concrete Motivating Example

ESP32JTAG is the clearest example.

One physical ESP32JTAG box may in principle expose multiple capture channels or
other separable hardware resources. Because of that:

- same physical instrument is not always the same as same capability
- same capability is not always the same as same sub-resource

Current AEL mostly collapses these distinctions to one thing:

- the instrument instance / endpoint

## Distinctions That Must Stay Clear

The following are different concepts:

- same physical instrument
- same capability
- same sub-resource / channel

Examples:

- two tests may touch the same ESP32JTAG box
- both may want `gpio_in`
- but they may want different channels

Today, AEL does not model that difference formally in runtime ownership.

## Likely Exclusivity Rules

For ESP32JTAG-like instruments, the following actions should likely be treated
as whole-device exclusive unless proven otherwise:

- SWD/JTAG attach
- flash/program/load
- reset control
- target halt/resume/debug state control
- global mode changes
- global capture/sampling reconfiguration

Some actions might be shareable in principle if modeled correctly:

- passive GPIO/logic capture on disjoint channels
- passive observation on independent input pins
- possibly some disjoint output/input cases, if the hardware guarantees safe
  separation

This is only conceptual today. It is not current runtime support.

## Current Limitation

AEL does not yet formally support:

- channel-level ownership
- concurrent owners inside one physical instrument
- capability-partition arbitration

Therefore, shareable same-instrument use is not yet a supported runtime model.

## Minimum Future Abstraction

If this is ever implemented, the minimum correct abstraction would likely need:

- instrument instance
- capability
- sub-resource / channel
- access mode
- ownership policy

Example access modes:

- `exclusive`
- `shared_read`
- `shared_if_disjoint`
- `global_config_exclusive`

These are only the minimum vocabulary needed to express the problem correctly.

## Scope Boundary

This note is:

- a design/architecture note only
- not a commitment to implement now
- not a change to current runtime claims
- not a statement that AEL already supports shareable sub-resource concurrency

## Bottom Line

Today, AEL supports whole-instrument-instance style ownership and locking.

Today, AEL does not support formal sub-resource/channel sharing inside one
instrument.

If AEL ever supports shareable same-instrument concurrency, it will need an
explicit abstraction for:

- instrument instance
- capability
- sub-resource / channel
- access mode
- ownership policy
