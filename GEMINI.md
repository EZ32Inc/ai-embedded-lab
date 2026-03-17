# Gemini CLI Foundational Mandates for AEL

## 1. Index of Truth (Absolute Priority)
Before searching the repository, you MUST consult these core documents to establish the "Product Truth":
1.  **`README.md`**: Project intro, mission, and "Natural-Language-First" usage examples.
2.  **`docs/agent_answering_guide.md`**: Answering discipline, Truth Layers, and source prioritization rules.
3.  **`docs/specs/ael_user_facing_response_policy_v0_1.md`**: Five-step response structure (Capability + Role + Plan + Constraint + Proceed).
4.  **`docs/agent_index/user_question_routing_v0_1.md`**: Trigger classification and internal routing logic.
5.  **`skills/respond_to_board_instrument_questions.md`**: Expert behavior for hardware-related inquiries.
6.  **`docs/specs/ael_architecture_v0_2.md`**: The current 6-part system architecture reference.

## 2. Response Routing & Discipline (The Gate)
- **Gate before Search**: When a user asks about AEL capability, board/instrument usage, or requests to create/run a test, you MUST NOT start with repository search or command listing.
- **Mandatory Policy Loading**: You must first resolve the routing via `docs/agent_index/user_question_routing_v0_1.md`.
- **Answering Mode**: Your response MUST follow the policy in `ael_user_facing_response_policy_v0_1.md`.
- **Avoid Command Dumps**: Do not provide lists of shell commands or script names unless the user explicitly asks for manual steps.

## 3. Truth Layering & Sourcing
- Follow the Truth Layers defined in `docs/agent_answering_guide.md`.
- **Product Truth > Implementation Truth**: Prioritize explaining *what* AEL can do and *how* it will execute, over *where* the code or scripts are located.

## 4. Real-World Hardware Confirmation
- **No Implicit Assumption**: A repo config is a *reference*, not proof of the user's setup.
- **Clarification First**: For any known-board request, you must output a structured "Known vs Assumed vs Needed" section before claiming readiness to run.
