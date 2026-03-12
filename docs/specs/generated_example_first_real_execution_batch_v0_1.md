# Generated Example First Real Execution Batch v0.1

## Purpose

This note defines the first non-governance batch that should happen when the
project is ready to move into generated-example execution.

## First Choice If Hardware Provisioning Happens First

Run a small UART execution batch:

- `rp2040_uart_banner`
- or `stm32f103_uart_banner`

Reason:
- these are the least structurally blocked generated examples
- the main missing piece is bench setup, not generation policy

## First Choice If Contract Completion Happens First

Complete one ADC external-input contract:

- recommended first target: `stm32f103_adc_banner`

Reason:
- it moves one blocked ADC example from "formally complete but blocked" toward
  execution-readiness without requiring a broad execution campaign

## Do Not Make This First Batch

- broad runtime validation across all generated examples
- broad ESP32 generated-example runtime claims
- USB example execution expansion
- new vendor-family expansion

## Working Rule

The first real execution batch should remove one blocker, not create many new
partially-runnable paths.
