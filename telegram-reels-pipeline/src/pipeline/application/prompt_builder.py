"""Prompt builder — constructs agent prompts from AgentRequest components."""

from __future__ import annotations

from pipeline.domain.models import AgentRequest


def build_agent_prompt(request: AgentRequest) -> str:
    """Construct a full prompt string from an AgentRequest.

    Reads step file and agent definition contents, appends prior artifact
    paths, elicitation context, and attempt history.
    """
    sections: list[str] = []

    # Stage requirements from the step file
    step_content = request.step_file.read_text()
    sections.append(f"## Stage Requirements\n\n{step_content}")

    # Agent definition (persona + knowledge)
    agent_content = request.agent_definition.read_text()
    sections.append(f"## Agent Definition\n\n{agent_content}")

    # Prior artifacts (file paths, not inline content)
    if request.prior_artifacts:
        artifact_lines = "\n".join(f"- {path}" for path in request.prior_artifacts)
        sections.append(f"## Prior Artifacts\n\n{artifact_lines}")

    # Elicitation context (user preferences from Router Agent)
    if request.elicitation_context:
        context_lines = "\n".join(f"- {k}: {v}" for k, v in request.elicitation_context.items())
        sections.append(f"## Elicitation Context\n\n{context_lines}")

    # Attempt history (QA feedback from prior rework cycles)
    if request.attempt_history:
        history_parts: list[str] = []
        for i, attempt in enumerate(request.attempt_history, 1):
            lines = "\n".join(f"  - {k}: {v}" for k, v in attempt.items())
            history_parts.append(f"### Attempt {i}\n{lines}")
        sections.append("## Attempt History\n\n" + "\n\n".join(history_parts))

    # Execution environment — always last
    sections.append(
        "## Execution Environment\n\n"
        "You are running as a Claude Code subprocess with tool access (Bash, Read, Write, Edit).\n"
        "Your working directory is a dedicated workspace for this pipeline run.\n\n"
        "**CRITICAL OUTPUT RULES**:\n\n"
        "- Use the Write tool to create each output file listed in Expected Outputs above\n"
        "- Write files to the current working directory (not subdirectories)\n"
        "- For JSON outputs: write valid JSON files directly, no markdown wrapping\n"
        "- You may use Bash to run CLI tools (yt-dlp, ffmpeg, etc.) as needed\n"
        "- If you cannot write files, output ONLY the raw content to stdout as a fallback"
    )

    return "\n\n".join(sections)
