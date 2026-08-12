"""Custom target registration loaded by native PyRIT configuration."""

from __future__ import annotations

import os

from genai_red_teaming_accelerator.pyrit_config import load_pyrit_catalog
from genai_red_teaming_accelerator.pyrit_targets import create_target_async

try:
    from pyrit.models.parameter import Parameter
    from pyrit.setup.pyrit_initializer import PyRITInitializer
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyRIT is required to load CatalogTargetInitializer") from exc


class CatalogTargetInitializer(PyRITInitializer):
    """Register configured customer targets and datasets for native PyRIT commands."""

    catalog_path: str = ""

    @property
    def supported_parameters(self) -> list[Parameter]:
        return []

    async def initialize_async(self) -> None:
        from pyrit.memory import CentralMemory
        from pyrit.models import SeedDataset
        from pyrit.registry import TargetRegistry

        path = os.getenv("RTA_PYRIT_TARGETS", self.catalog_path)
        if not path:
            raise ValueError("The initializer must define catalog_path or RTA_PYRIT_TARGETS")
        catalog = load_pyrit_catalog(path)
        authorization = os.getenv(catalog.authorization.environment)
        if authorization is None or authorization.casefold() != catalog.authorization.expected_value.casefold():
            raise ValueError(
                f"{catalog.authorization.environment}={catalog.authorization.expected_value!r} "
                "is required after authorization"
            )

        if catalog.datasets:
            datasets = [
                SeedDataset(
                    dataset_name=dataset.name,
                    seed_type="objective",
                    seeds=[{"value": objective} for objective in dataset.objectives],
                )
                for dataset in catalog.datasets
            ]
            await CentralMemory.get_memory_instance().add_seed_datasets_to_memory_async(
                datasets=datasets,
                added_by="red-teaming-accelerator",
            )

        registry = TargetRegistry.get_registry_singleton()
        instances: dict[str, object] = {}
        for definition in catalog.targets:
            instance = await create_target_async(definition)
            instances[definition.name] = instance
            registry.instances.register(
                instance,
                name=definition.name,
                tags={tag: "" for tag in definition.tags},
                metadata={"configured_target": definition.name, "target_type": definition.target.type},
            )

        scorer = instances[catalog.scorer_target]
        registry.instances.register(scorer, name="objective_scorer_chat", tags={"scorer": "default"})
        registry.instances.register(scorer, name="openai_chat", tags={"scorer": "fallback"})
        registry.instances.register(scorer, name="adversarial_chat", tags={"adversarial": "fallback"})
