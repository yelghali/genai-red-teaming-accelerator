"""Initializers discovered and executed by PyRIT 1.0.1."""

from pathlib import Path

from pyrit.setup.initializers.scorers import ScorerInitializer

from genai_red_teaming_accelerator.pyrit_initializer import CatalogTargetInitializer


class AConfiguredTargets(CatalogTargetInitializer):
    """Load the target catalog adjacent to this native PyRIT configuration."""

    catalog_path = str(Path(__file__).with_name("targets.yaml"))


class BConfiguredScorers(ScorerInitializer):
    """Build PyRIT scorers after the configured scorer target is registered."""
