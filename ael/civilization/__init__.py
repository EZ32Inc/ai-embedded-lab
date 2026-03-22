"""AEL Civilization Engine — internal AEL module.

This is an internal AEL layer.  AEL components import from here.
The Civilization Engine is the only code in AEL that talks to the
Experience Engine; no other AEL module may import from experience_engine.

Public API:
    from ael.civilization import CivilizationEngine, CivilizationContext

    # Before a run
    ctx = CivilizationEngine.get_context(board_id, test_name)

    # Structured queries
    recommended = CivilizationEngine.get_recommended_path(intent, context)
    avoid       = CivilizationEngine.get_avoid_paths(intent, context)
    skills      = CivilizationEngine.get_relevant_skills(intent, context)

    # After a run
    exp_id = CivilizationEngine.record_run(board_id, test_name, ok, stages, ...)

    # Feedback
    CivilizationEngine.feedback(exp_id, correct=True)
"""

from ael.civilization.engine import CivilizationEngine
from ael.civilization.context import CivilizationContext

__all__ = ["CivilizationEngine", "CivilizationContext"]
