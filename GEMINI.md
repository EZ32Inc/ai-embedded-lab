# Gemini CLI Foundational Mandates for AEL

## 1. Response Routing & Discipline (CRITICAL)
- **Gate before Search**: When a user asks about AEL capability, board/instrument usage, or requests to create/run a test, you MUST NOT start with repository search or command listing.
- **Mandatory Policy Loading**: Before constructing a technical answer, you must first consult `docs/specs/ael_user_facing_response_policy_v0_1.md` and `docs/agent_index/user_question_routing_v0_1.md`.
- **Answering Mode**: Your response must follow the sequence: **[System Capability] -> [Instrument Role] -> [Execution Plan] -> [Real-world Constraints] -> [Ask to Proceed]**.
- **Avoid Command Dumps**: Do not provide lists of shell commands or script names unless the user explicitly asks for manual steps.

## 2. Skill Activation
- When a user inquiry matches board/instrument usage or execution requests, proactively activate the skill `skills/respond_to_board_instrument_questions.md` to guide your behavior.

## 3. Truth Layering & Sourcing
- Follow the Truth Layers defined in `docs/agent_answering_guide.md`.
- **Product Truth > Implementation Truth**: Prioritize explaining *what* AEL can do and *how* it will execute, over *where* the code or scripts are located.

## 4. Real-World Hardware Confirmation
- **No Implicit Assumption**: A repo config is a *reference*, not proof of the user's setup.
- **Clarification First**: For any known-board request, you must output a structured "Known vs Assumed vs Needed" section before claiming readiness to run.
