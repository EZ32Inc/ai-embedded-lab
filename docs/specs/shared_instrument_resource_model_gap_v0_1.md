# Shared Instrument Resource Model Gap v0.1

## Current model

Current AEL resource ownership is mostly modeled with keys like:

- `dut:<id>`
- `probe:<host>:<port>`
- `probe_path:<config>`
- `serial:<port>`
- `instrument:<id>:<host>:<port>`

Current runtime locking is applied directly to those whole-resource keys.

For control instruments, this means ownership is currently centered on the
whole instrument instance/config or endpoint, not on capability or channel.

## Future model needed

If AEL ever needs to remove unnecessary same-instrument blocking safely, the
minimum future model would need to distinguish:

- instrument instance
- capability
- sub-resource / channel
- access mode
- ownership policy

## Current model vs future model gap

Current AEL can express:

- same DUT vs different DUT
- same control-instrument instance vs different control-instrument instance
- same serial endpoint vs different serial endpoint
- same meter endpoint vs different meter endpoint

Current AEL cannot formally express:

- same physical instrument but different capability usage
- same capability but different channels
- sub-resource shareability rules
- capability-partition arbitration

## Why the gap matters

Today, AEL mostly collapses these three things together:

- same physical instrument
- same capability
- same sub-resource

That is acceptable when whole-device exclusivity is correct, but it becomes too
coarse if part of the device is safely shareable.

## Current 4-worker baseline relevance

The current 4-worker default suite proves that:

- separate DUT identity can and should remove false DUT-level blocking
- shared control-instrument blocking remains at the whole-device level

This gives a clean baseline for judging whether any remaining blocking is truly
shared or only collapsed by overly coarse ownership.

