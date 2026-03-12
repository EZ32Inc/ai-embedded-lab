# Generated Example Next Move Triage v0.1

## Purpose

This note answers one immediate planning question:

- what can actually move next, and what kind of work does it require?

## Requires Hardware Provisioning First

- `rp2040_uart_banner`
- `stm32f103_uart_banner`

Reason:
- first meaningful live runtime-validation attempts need a real UART setup path

## Requires Contract Completion First

- ADC generated examples

Recommended first contract-completion task:
- define one explicit external analog-input contract for
  `stm32f103_adc_banner`

Reason:
- this removes a real blocker without requiring a broad runtime campaign

## Should Remain Observation-Only For Now

- ESP32 generated examples on the current meter-backed path

Reason:
- generation/build status is still valid
- runtime promotion should remain conservative while the meter path is unstable

## Immediate Planning Rule

Choose one of these next:

1. provision one UART path, or
2. complete one ADC external-input contract

Do not start with:
- broad multi-example runtime execution
- broad ESP32 generated-example runtime claims
- new family expansion
