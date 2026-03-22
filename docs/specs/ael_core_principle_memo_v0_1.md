# AEL Core Principle Memo
## Outcome-First Engineering & Hidden Complexity

**Status:** Draft
**Date:** 2026-03-22
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 1. Problem Statement

Modern embedded development ecosystems (e.g., SDKs like ESP-IDF) expose a large amount of technical detail:

- SDK versions
- Toolchains
- Driver APIs
- Build systems
- Hardware-specific constraints

While necessary at the system level, these details create a significant cognitive burden for users.

Most users do not care about these details.
What they care about is:

> How do I solve my problem in the best possible way?

---

## 2. AEL Paradigm Shift

AEL introduces a fundamental shift in how engineering systems are used:

| Traditional Model | AEL Model |
|------------------|-----------|
| Learn system → use tools → get result | Express intent → system delivers result |
| User chooses SDK / version / tools | System chooses optimal solution |
| User handles complexity | System absorbs complexity |

**Core Shift:**

> From "understanding systems" → to "expressing intent"

---

## 3. Core Principle

Users should not need to understand SDKs, versions, tools, or low-level concepts to achieve their goals. AEL handles all underlying complexity.

This means:

**Users do NOT need to know:**
- Which SDK is used (e.g., ESP-IDF)
- Which version (e.g., 5.x vs 6.0)
- Which MCU or OS is selected
- How drivers or toolchains work

**Users ONLY need to specify:**
- What they want to achieve
- What outcome they expect

---

## 4. System Responsibility Model

AEL introduces a strict separation of responsibilities:

### User Layer (Intent)
Users express:
- Goals
- Constraints (optional)
- Preferences (optional)

Example:
> "I want to read data from an FPGA using ESP32 over SPI and display it in a browser."

### AEL Decision Layer (Intelligence)
AEL determines:
- Platform (ESP32 / STM32 / etc.)
- SDK and version (e.g., IDF 5.2 vs 6.0)
- Architecture (SPI, WebSocket, etc.)
- Implementation path (examples, configurations)
- Known pitfalls and best practices

This layer replaces user decision-making.

### Execution Layer (Backend)
Underlying systems (e.g., ESP-IDF) are used as:
- Capability providers
- Execution engines

They are used, but never exposed as required knowledge.

---

## 5. Optimal Solution Principle

AEL does not provide "a possible way" — it provides:

> **The best known solution for the user's goal**

This includes:
- Stability
- Compatibility
- Performance
- Proven implementation paths

Users receive a working solution, not a list of options.

---

## 6. Version Abstraction

SDK versions are treated as internal system variables, not user-facing concepts.

AEL may choose:
- Newer versions (for new capabilities)
- Older versions (for stability or compatibility)

**User-facing behavior:**
- Default: no version exposure
- On request: full transparency

Example:
> User: "Why did you choose this version?"
> AEL: Provides reasoning (stability, compatibility, validated paths)

---

## 7. Transparency Principle

AEL hides complexity by default, but reveals it on demand.

- **Default mode:** No SDK/version/tool exposure
- **Advanced mode:** Users can inspect decisions, override choices, force specific versions

---

## 8. Civilization Layer (Knowledge System)

AEL is not only executing tasks — it accumulates engineering knowledge.

Each solution is:
- Proven
- Structured
- Reusable

This forms the AEL Civilization: a continuously growing set of validated engineering solutions.

---

## 9. Consultation Capability

AEL supports pre-execution guidance:

Users can ask:
> "What is the best way to build this system?"

AEL responds with:
- Recommended architecture
- Technology choices
- Trade-offs
- Execution-ready plan

---

## 10. Final Definition

> AEL is not a tool for using SDKs.
> AEL is a system that delivers optimal engineering outcomes without requiring users to understand the underlying systems.

---

## 11. Key Takeaway

> Users don't need to know how it works.
> They only need to say what they want.
> AEL takes care of the rest.

---

*Extracted from AEL design discussion. Date: 2026-03-22*
