# Legacy Backend Shim Alignment

## Purpose

Use this skill when an old backend driver name still appears in configs, but
its implementation overlaps with newer reference backends.

## Rule

Do not keep two independent implementations alive if one is clearly legacy.

Instead:

1. keep the old driver name runnable
2. convert the old backend module into a thin compatibility shim
3. forward each supported action to the current reference backend
4. document that new work must land in the reference backend, not the shim

## Why

This reduces behavior drift while keeping old configs operational.

## Typical Trigger

- a legacy backend still mixes responsibilities already owned by newer
  package-style backends
- removing the driver name immediately would be too disruptive
