from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).parents[1]
MICROSOFT_PYTHON_INDEX = "https://packagefeedproxy.microsoft.io/pypi/simple"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
YAML_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


def test_obsolete_wrapper_and_deterministic_demo_are_removed() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'rta = "genai_red_teaming_accelerator.redteam_cli:main"' in pyproject
    assert 'foundry-scan = "genai_red_teaming_accelerator.foundry_cli:main"' in pyproject
    assert not (ROOT / "src/genai_red_teaming_accelerator/cli.py").exists()
    assert not (ROOT / "src/genai_red_teaming_accelerator/demo.py").exists()
    assert not (ROOT / "code").exists()
    assert not (ROOT / "requirements.txt").exists()
    assert not (ROOT / "requirements-scan.txt").exists()


def test_native_configuration_is_the_primary_pyrit_interface() -> None:
    config = (ROOT / "configs/pyrit/pyrit-config.yaml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile.pyrit-scan").read_text(encoding="utf-8")

    assert "initialization_scripts:" in config
    assert "configs/pyrit/initializer.py" in config
    assert "pyrit_scan airt.jailbreak" in readme
    assert 'ENTRYPOINT ["pyrit_scan"]' in dockerfile
    assert "run_pyrit_scan.py" not in dockerfile


def test_foundry_iac_is_provider_generic_and_secure_by_default() -> None:
    content = (ROOT / "infra/foundry/main.bicep").read_text(encoding="utf-8")
    anthropic = (ROOT / "infra/foundry/anthropic.bicep").read_text(encoding="utf-8")

    assert content.count("Microsoft.CognitiveServices/accounts@") == 1
    assert content.count("Microsoft.CognitiveServices/accounts/projects@") == 1
    assert "param modelDeployments array" in content
    assert "for deployment in modelDeployments" in content
    assert "format: deployment.publisher" in content
    assert "disableLocalAuth: true" in content
    assert "format: 'Anthropic'" in anthropic
    assert "modelProviderData:" in anthropic
    assert "organizationName string =" not in anthropic


def test_only_supported_runtime_dependency_generations_remain() -> None:
    content = "\n".join(
        path.read_text(encoding="utf-8") for path in [ROOT / "pyproject.toml", *sorted((ROOT / "src").rglob("*.py"))]
    ).lower()

    assert "pyrit==0.8" not in content
    assert "azure-ai-evaluation" not in content
    assert "litellm" not in content
    assert "anthropic_api_key" not in content


def test_python_dependency_installs_use_the_microsoft_index() -> None:
    install_surfaces = [
        ROOT / "Dockerfile.pyrit-scan",
        ROOT / "compose.yaml",
        ROOT / ".devcontainer/devcontainer.json",
        ROOT / ".github/workflows/accelerator-quality.yml",
        ROOT / "README.md",
        ROOT / "docs/running-scans.md",
        ROOT / "docs/workshop.md",
    ]

    for path in install_surfaces:
        content = path.read_text(encoding="utf-8")
        assert MICROSOFT_PYTHON_INDEX in content, f"Microsoft Python index missing from {path.relative_to(ROOT)}"
        assert "https://pypi.org/simple" not in content, f"Public PyPI default remains in {path.relative_to(ROOT)}"


def test_publication_documents_have_no_template_placeholders() -> None:
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    workshop = (ROOT / "docs/workshop.md").read_text(encoding="utf-8")

    assert "REPO OWNER" not in support
    assert "REPO MAINTAINER" not in support
    assert "PROJECT or PRODUCT" not in support
    assert "TODO:" not in support
    assert "SECURITY.md" in support

    marker, front_matter, body = workshop.split("---", maxsplit=2)
    metadata = yaml.safe_load(front_matter)
    assert marker == ""
    assert metadata["published"] is True
    assert metadata["type"] == "workshop"
    assert metadata["title"] == "Red Teaming Accelerator Workshop"
    assert metadata["short_title"] == "RTA Workshop"
    assert "# Red Teaming Accelerator Workshop" in body
    assert body.count("\n---\n") == 14
    assert "](../" not in body


def test_running_scan_guide_covers_every_supported_target_path() -> None:
    guide = (ROOT / "docs/running-scans.md").read_text(encoding="utf-8")

    required_sections = [
        "## 3. Scan a model with native PyRIT",
        "## 4. Create a portal-visible Foundry model evaluation",
        "## 5. Scan a JSON HTTP API",
        "## 6. Scan an authenticated browser UI",
        "## 7. Review results",
    ]
    for section in required_sections:
        assert section in guide

    assert "rta plan baseline-pyrit --config configs/redteam.yaml --json" in guide
    assert "rta run baseline-foundry --config configs/redteam.yaml" in guide
    assert "rta run --config configs/examples/api-redteam.yaml" in guide
    assert "rta run --config configs/examples/ui-redteam.yaml" in guide
    assert "`rta validate` validates all referenced configuration files" in guide
    assert "All three are offline" in guide
    assert "REDTEAM_SCOPE_APPROVED=true" in guide
    assert "Put `{PROMPT}` exactly once" in guide
    assert "Target URLs contain no embedded credentials" in guide


def test_local_documentation_links_resolve_inside_the_repository() -> None:
    documents = [
        ROOT / "README.md",
        ROOT / "configs/README.md",
        ROOT / "docs/running-scans.md",
        ROOT / "docs/workshop.md",
    ]

    for document in documents:
        for raw_target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().split(maxsplit=1)[0]
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            resolved = (document.parent / unquote(parsed.path)).resolve()
            assert resolved.is_relative_to(ROOT), f"Link escapes repository in {document.relative_to(ROOT)}: {target}"
            assert resolved.exists(), f"Broken link in {document.relative_to(ROOT)}: {target}"


def test_documented_yaml_examples_parse() -> None:
    documents = [ROOT / "docs/running-scans.md", ROOT / "docs/workshop.md"]

    for document in documents:
        blocks = YAML_FENCE.findall(document.read_text(encoding="utf-8"))
        assert blocks, f"No YAML examples found in {document.relative_to(ROOT)}"
        for block in blocks:
            assert yaml.safe_load(block) is not None, f"Empty YAML example in {document.relative_to(ROOT)}"


def test_shared_engine_selector_delegates_to_native_apis() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    config = (ROOT / "configs/redteam.yaml").read_text(encoding="utf-8")
    runner = (ROOT / "src/genai_red_teaming_accelerator/redteam.py").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/accelerator-quality.yml").read_text(encoding="utf-8")

    assert 'rta = "genai_red_teaming_accelerator.redteam_cli:main"' in pyproject
    assert "engine: pyrit" in config
    assert "engine: foundry" in config
    assert "ScenarioRegistry" in runner
    assert "FoundryRunner" in runner
    assert "while " not in runner
    assert "rta-pyrit-data" in compose
    assert "rta plan baseline-pyrit" in workflow
    assert "rta plan baseline-foundry" in workflow
    assert "rta plan custom-pyrit" in workflow
    assert "rta plan --config configs/examples/api-redteam.yaml --json" in workflow
    assert "rta plan --config configs/examples/ui-redteam.yaml --json" in workflow
    assert 'test "$(id -u)" != 0 && python -m pip check' in workflow
    assert "p.chromium.launch(headless=True)" in workflow


def test_legacy_prefix_is_limited_to_existing_azure_resource_ids() -> None:
    legacy_prefix = "g" + "rta"
    allowed_ids = {
        f"{legacy_prefix}fd08120131",
        f"{legacy_prefix}-redteam",
        f"{legacy_prefix}-openai",
        f"{legacy_prefix}-mistral",
        f"{legacy_prefix}-anthropic",
    }
    roots = [
        ROOT / "README.md",
        ROOT / "compose.yaml",
        ROOT / "pyproject.toml",
        ROOT / ".devcontainer",
        ROOT / ".github",
        ROOT / "configs",
        ROOT / "docs",
        ROOT / "infra",
        ROOT / "src",
        ROOT / "tests",
    ]
    text_extensions = {".json", ".md", ".py", ".toml", ".yaml", ".yml", ".bicep"}
    violations: list[str] = []

    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in text_extensions:
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if legacy_prefix not in line.casefold():
                    continue
                if not any(resource_id in line.casefold() for resource_id in allowed_ids):
                    violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")

    assert not violations, "Legacy product prefix remains outside deployed Azure IDs:\n" + "\n".join(violations)
