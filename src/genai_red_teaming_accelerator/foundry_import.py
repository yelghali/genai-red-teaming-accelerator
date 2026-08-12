"""Publish Foundry cloud result snapshots into PyRIT memory for Co-PyRIT."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pyrit.models import (
    AtomicAttackIdentifier,
    AttackIdentifier,
    AttackOutcome,
    AttackResult,
    ComponentIdentifier,
    Conversation,
    MessagePiece,
    Score,
    TargetIdentifier,
)

if TYPE_CHECKING:
    from pyrit.memory import MemoryInterface

    from genai_red_teaming_accelerator.foundry import FoundryRunResult

_MODULE = "genai_red_teaming_accelerator.foundry_import"


@dataclass(frozen=True, slots=True)
class FoundryImportSummary:
    """Counts from one idempotent Foundry-to-PyRIT snapshot publication."""

    imported: int
    already_present: int
    skipped_without_messages: int


def _text(value: Any) -> str:
    """Normalize OpenAI-style message content to displayable text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                candidate = item.get("text") or item.get("content")
                parts.append(candidate if isinstance(candidate, str) else json.dumps(item, sort_keys=True))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if value is None:
        return ""
    return json.dumps(value, sort_keys=True) if isinstance(value, dict) else str(value)


def _message_piece(
    *,
    raw: dict[str, Any],
    conversation_id: str,
    sequence: int,
    default_role: str,
    metadata: dict[str, Any],
) -> MessagePiece:
    role = str(raw.get("role") or default_role).lower()
    allowed_roles = {"system", "user", "assistant", "tool", "developer"}
    if role not in allowed_roles:
        role = default_role
    return MessagePiece(
        role=role,  # type: ignore[arg-type]
        conversation_id=conversation_id,
        sequence=sequence,
        original_value=_text(raw.get("content")),
        prompt_metadata=metadata,
    )


def _primary_result(item: dict[str, Any]) -> dict[str, Any]:
    results = item.get("results") or []
    if not isinstance(results, list):
        return {}
    typed = [result for result in results if isinstance(result, dict)]
    return next((result for result in typed if result.get("type") == "azure_ai_red_team"), typed[0] if typed else {})


def _attack_success(result: dict[str, Any]) -> bool | None:
    properties = result.get("properties") or {}
    value = properties.get("attack_success") if isinstance(properties, dict) else None
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.casefold() in {"true", "false"}:
        return value.casefold() == "true"
    return None


def _timestamp(item: dict[str, Any]) -> datetime:
    value = item.get("created_at")
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=UTC)
        except (OSError, OverflowError, ValueError):
            pass
    return datetime.now(UTC)


def _target_identifier(result: FoundryRunResult) -> TargetIdentifier:
    run = result.run if isinstance(result.run, dict) else {}
    data_source = run.get("data_source") or {}
    target = data_source.get("target") or {} if isinstance(data_source, dict) else {}
    model_name = result.target_deployment or target.get("model") or target.get("name")
    return TargetIdentifier(
        class_name="FoundryCloudTarget",
        class_module=_MODULE,
        endpoint=result.project_endpoint,
        model_name=str(model_name) if model_name else None,
        underlying_model_name=result.target_model,
    )


def _labels(result: FoundryRunResult, *, item_id: str, risk: str, technique: str) -> dict[str, str]:
    labels = {str(key): str(value) for key, value in result.labels.items()}
    labels.update(
        {
            "engine": "foundry",
            "source": "foundry_cloud_snapshot",
            "foundry_eval_id": result.eval_id,
            "foundry_run_id": result.run_id,
            "foundry_item_id": item_id,
            "risk_category": risk,
            "attack_technique": technique,
        }
    )
    return labels


def import_foundry_result(*, result: FoundryRunResult, memory: MemoryInterface) -> FoundryImportSummary:
    """Import completed Foundry output items without claiming they were executed by PyRIT."""
    if result.status != "completed":
        raise ValueError("Only completed Foundry runs can be published to Co-PyRIT")

    target_identifier = _target_identifier(result)
    imported = 0
    already_present = 0
    skipped_without_messages = 0

    for index, raw_item in enumerate(result.output_items):
        if not isinstance(raw_item, dict):
            skipped_without_messages += 1
            continue
        item_id = str(raw_item.get("id") or raw_item.get("datasource_item_id") or index)
        identity = f"foundry://{result.eval_id}/{result.run_id}/{item_id}"
        attack_result_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{identity}/attack"))
        if memory.get_attack_results(attack_result_ids=[attack_result_id]):
            already_present += 1
            continue

        sample = raw_item.get("sample") or {}
        if not isinstance(sample, dict):
            skipped_without_messages += 1
            continue
        input_messages = sample.get("input") or []
        output_messages = sample.get("output") or []
        if not isinstance(input_messages, list) or not isinstance(output_messages, list):
            skipped_without_messages += 1
            continue
        messages = [message for message in input_messages if isinstance(message, dict)] + [
            message for message in output_messages if isinstance(message, dict)
        ]
        if not messages:
            skipped_without_messages += 1
            continue

        evaluation = _primary_result(raw_item)
        properties = evaluation.get("properties") or {}
        properties = properties if isinstance(properties, dict) else {}
        technique = str(properties.get("attack_technique") or "unknown")
        risk = str(evaluation.get("metric") or evaluation.get("name") or "unknown")
        success = _attack_success(evaluation)
        reason = str(evaluation.get("reason") or "Foundry evaluator did not provide a rationale")
        conversation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{identity}/conversation"))
        timestamp = _timestamp(raw_item)
        common_metadata = {
            "source": "foundry_cloud_snapshot",
            "foundry_eval_id": result.eval_id,
            "foundry_run_id": result.run_id,
            "foundry_item_id": item_id,
            "foundry_report_url": result.report_url or "",
            "cloud_inputs_may_be_redacted": True,
        }
        pieces: list[MessagePiece] = []
        for sequence, message in enumerate(messages):
            default_role = "user" if sequence < len(input_messages) else "assistant"
            pieces.append(
                _message_piece(
                    raw=message,
                    conversation_id=conversation_id,
                    sequence=sequence,
                    default_role=default_role,
                    metadata=common_metadata,
                )
            )
        last_response = next((piece for piece in reversed(pieces) if piece.api_role == "assistant"), None)

        score = None
        if last_response is not None:
            score = Score(
                score_value="true" if success else "false" if success is False else "unknown",
                score_value_description="Foundry cloud attack_success",
                score_type="true_false" if success is not None else "unknown",
                score_category=[risk],
                score_rationale=reason,
                score_metadata={
                    "foundry_score": float(evaluation["score"])
                    if isinstance(evaluation.get("score"), (int, float))
                    else -1.0,
                    "foundry_passed": int(bool(evaluation.get("passed"))),
                },
                scorer_class_identifier=ComponentIdentifier(
                    class_name="FoundryCloudEvaluator",
                    class_module=_MODULE,
                    params={"metric": risk},
                ),
                message_piece_id=last_response.id,
                objective=f"Assess {risk} under {technique}",
            )

        attack_identifier = AttackIdentifier(
            class_name="FoundryCloudSnapshot",
            class_module=_MODULE,
            params={
                "attack_technique": technique,
                "attack_complexity": str(properties.get("attack_complexity") or "unknown"),
                "source": "foundry_cloud",
            },
            objective_target=target_identifier,
        )
        outcome = (
            AttackOutcome.SUCCESS
            if success is True
            else AttackOutcome.FAILURE
            if success is False
            else AttackOutcome.ERROR
            if sample.get("error")
            else AttackOutcome.UNDETERMINED
        )
        labels = _labels(result, item_id=item_id, risk=risk, technique=technique)
        attack_result = AttackResult(
            attack_result_id=attack_result_id,
            conversation_id=conversation_id,
            objective=f"Foundry cloud snapshot: assess {risk} via {technique}",
            atomic_attack_identifier=AtomicAttackIdentifier.build(attack_identifier=attack_identifier),
            last_response=last_response,
            last_score=score,
            executed_turns=max(1, sum(piece.api_role == "assistant" for piece in pieces)),
            outcome=outcome,
            outcome_reason=reason,
            timestamp=timestamp,
            metadata={
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat(),
                "provenance": "imported_foundry_cloud_snapshot",
                "foundry_report_url": result.report_url,
                "foundry_result_path": result.result_path,
            },
            labels=labels,
            targeted_harm_categories=[] if risk == "unknown" else [risk],
            error_message=_text(sample.get("error")) or None,
            error_type="FoundryCloudSampleError" if sample.get("error") else None,
        )

        memory.add_conversation_to_memory(
            conversation=Conversation(conversation_id=conversation_id, target_identifier=target_identifier)
        )
        memory.add_message_pieces_to_memory(message_pieces=pieces)
        if score is not None:
            memory.add_scores_to_memory(scores=[score])
        memory.add_attack_results_to_memory(attack_results=[attack_result])
        imported += 1

    return FoundryImportSummary(
        imported=imported,
        already_present=already_present,
        skipped_without_messages=skipped_without_messages,
    )
