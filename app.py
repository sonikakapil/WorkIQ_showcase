from __future__ import annotations

import html
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from services.memory_manager import MemoryManager
from services.workiq_client import WorkIQClient

try:
    from openai import AzureOpenAI
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    _AZURE_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - import guard for local envs
    AzureOpenAI = None  # type: ignore[assignment]
    DefaultAzureCredential = None  # type: ignore[assignment]
    get_bearer_token_provider = None  # type: ignore[assignment]
    _AZURE_IMPORT_ERROR = str(exc)

load_dotenv()

st.set_page_config(
    page_title="WorkIQ",
    page_icon="W",
    layout="wide",
    initial_sidebar_state="expanded",
)

TOP_QUICK_STARTS = {
    "workiq_command_center": {
        "feature": "WorkIQ",
        "label": "Tomorrow Command Center",
        "hint": "Tomorrow's priorities, stakeholder readout, conflicts, and prep.",
        "display_text": "Tomorrow Command Center",
        "prompt": (
            "Build my command center for tomorrow.\n\n"
            "Use my calendar, current work threads, and stakeholder context.\n\n"
            "Give me:\n"
            "- the 3 meetings that matter most\n"
            "- what each key stakeholder is likely to care about\n"
            "- any collisions, overlaps, or risks I should manage\n"
            "- what I should decide, delegate, or defer\n"
            "- the 3 prep moves that would most improve tomorrow\n\n"
            "Make it feel like a chief-of-staff briefing, not a meeting summary.\n"
            "End with: If I only do three things tonight, do these."
        ),
        "lens": textwrap.dedent(
            """
            Shape the answer as a sharp executive briefing.
            Prefer these section headings:
            ## Executive call
            ## Critical meetings
            ## Stakeholder readout
            ## Collisions and risks
            ## Decide / delegate / defer
            ## Tonight's three moves
            Keep it concrete, high-signal, and specific.
            """
        ).strip(),
    },
    "memory_continue": {
        "feature": "Memory",
        "label": "Continue From Earlier",
        "hint": "Continue from prior context instead of starting over.",
        "display_text": "Continue From Earlier",
        "prompt": (
            "Continue from our earlier discussion instead of starting over.\n\n"
            "Use what is already in context from this session and build forward.\n\n"
            "Give me:\n"
            "- what should be carried forward from the earlier answer\n"
            "- what has become more urgent or more important\n"
            "- the 5 highest-value follow-ups with owner, why, and next move\n"
            "- the single fastest unblock\n"
            "- what I should do in the next 24 hours\n\n"
            "Do not re-summarize everything from scratch. Preserve continuity."
        ),
        "lens": textwrap.dedent(
            """
            Shape the answer as a true continuation.
            Prefer these section headings:
            ## Carried forward
            ## What just became more urgent
            ## Highest-value follow-ups
            ## Fastest unblock
            ## Next 24 hours
            Make it obvious that memory is being used.
            """
        ).strip(),
    },
    "skills_draft": {
        "feature": "Skills",
        "label": "Draft What I Need",
        "hint": "Create ready-to-send outputs from current work context.",
        "display_text": "Draft What I Need",
        "prompt": (
            "Based on my current work context, draft the 3 messages I most likely need next.\n\n"
            "Return:\n"
            "- one executive follow-up note\n"
            "- one customer or stakeholder alignment message\n"
            "- one internal delegation or unblocker note\n\n"
            "For each draft:\n"
            "- give me a strong subject line\n"
            "- keep it concise and ready to send\n"
            "- make the tone appropriate to the audience\n"
            "- include the specific ask, owner, and next step\n\n"
            "Make the output practical enough that I could copy, edit lightly, and send."
        ),
        "lens": textwrap.dedent(
            """
            Shape the answer as practical output, not analysis.
            Prefer these section headings:
            ## Draft 1 - Executive follow-up
            ## Draft 2 - Stakeholder alignment
            ## Draft 3 - Internal delegation
            For each draft include:
            - Subject
            - Message
            - Why this matters
            The answer should feel immediately usable.
            """
        ).strip(),
    },
    "productivity_hub": {
        "feature": "Productivity",
        "label": "Productivity",
        "hint": "Meeting load, Teams pulse, and org visibility.",
        "display_text": "Productivity",
        "prompt": "",
        "lens": "",
        "opens_panel": True,
    },
}

PRODUCTIVITY_SCENARIOS = {
    "meeting_load_radar": {
        "feature": "Productivity",
        "label": "Meeting Load Radar",
        "skill": "meeting-cost-calculator",
        "display_text": "Meeting Load Radar",
        "prompt": textwrap.dedent(
            """
            Analyze my meeting load for this week like a ruthless staff chief.

            I want:
            - total meeting hours and approximate percentage of work time
            - the days that look overloaded
            - which recurring meetings are consuming the most time
            - which meetings should be shortened, delegated, or challenged
            - the practical time I could win back

            Do not stay descriptive. Recommend concrete reductions.
            """
        ).strip(),
        "lens": textwrap.dedent(
            """
            Shape the answer like a meeting economics review.
            Prefer these section headings:
            ## Executive take
            ## Meeting load snapshot
            ## Overload risks
            ## Most expensive recurring meetings
            ## What to shorten or challenge
            ## Time won back
            Use short bullets and hard judgment.
            """
        ).strip(),
    },
    "channel_pulse": {
        "feature": "Productivity",
        "label": "Channel Pulse",
        "skill": "channel-digest",
        "display_text": "Channel Pulse",
        "prompt": textwrap.dedent(
            """
            Give me a channel digest for what matters most right now across my Teams channels.

            I want:
            - the top decisions made recently
            - the action items that need me or affect my work
            - the most important mentions of me
            - the active discussions I should be aware of
            - the 3 things I should respond to or influence today

            Present it like a senior operator catching up fast, not like a thread transcript.
            """
        ).strip(),
        "lens": textwrap.dedent(
            """
            Shape the answer as a cross-channel control tower.
            Prefer these section headings:
            ## Cross-channel highlights
            ## Decisions made
            ## Action items needing you
            ## Mentions and watch-outs
            ## Debates to watch
            ## Today's response moves
            Keep it compressed and high-signal.
            """
        ).strip(),
    },
    "org_lens": {
        "feature": "Productivity",
        "label": "Org Lens",
        "skill": "org-chart",
        "display_text": "Org Lens",
        "prompt": textwrap.dedent(
            """
            Show me my org context and turn it into stakeholder intelligence.

            Give me:
            - my management chain and nearby org structure
            - the people around me who most influence priorities or decisions
            - who I should keep warm this week
            - where alignment risk may exist across the org
            - one smart outreach move for each key stakeholder cluster

            Blend org visibility with practical operating advice.
            """
        ).strip(),
        "lens": textwrap.dedent(
            """
            Shape the answer as stakeholder intelligence.
            Prefer these section headings:
            ## Org view
            ## Decision influence map
            ## Stakeholders to keep warm
            ## Alignment risks
            ## Best outreach moves
            If possible, include a compact org tree in a code block.
            """
        ).strip(),
    },
}

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are WorkIQ, an executive work copilot.

    Response rules:
    - Return clean markdown only
    - Do not use emojis
    - Do not use decorative symbols or icons
    - Do not use tables unless explicitly asked or clearly useful
    - Follow the working lens, but do not sound robotic
    - Be concrete, commercially useful, and action-oriented
    - Focus on priorities, decisions, risks, stakeholders, actions, and business impact
    - Avoid fluff and generic productivity advice
    - If asked to continue from earlier, clearly preserve continuity
    - If asked to draft messages, produce concise, sendable drafts
    - Prefer judgment over repetition

    Make each answer feel different in purpose and output shape.
    """
).strip()

REFINER_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an elite executive editor.

    Your task is to refine a grounded work answer into a sharper, more persuasive operating brief.

    Non-negotiable rules:
    - Preserve the underlying facts and intent
    - Do not invent people, meetings, decisions, dates, owners, or metrics
    - Remove repetition, filler, hedging, and generic advice
    - Prefer short sections, tight bullets, and decisive language
    - Make the output feel premium, crisp, and boardroom-ready
    - Keep markdown clean
    - No emojis
    - No decorative symbols
    - No tables unless the source clearly contains structured comparative content that benefits from one
    - If the source is thin, make it cleaner, not longer
    """
).strip()

APP_CSS = """
<style>
.block-container {
    max-width: 100%;
    padding-top: 3.2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 1.25rem;
}
[data-testid="stSidebar"] {
    min-width: 300px;
    max-width: 300px;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}
.wiq-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 1.1rem;
}
.wiq-mark {
    width: 2rem;
    height: 2rem;
    border-radius: 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.95rem;
    color: #111827;
    background: linear-gradient(180deg, #f59e0b, #fbbf24);
    box-shadow: 0 10px 24px rgba(245, 158, 11, 0.18);
}
.wiq-title {
    font-size: 1.55rem;
    font-weight: 650;
    line-height: 1.05;
    letter-spacing: -0.02em;
}
.wiq-kicker {
    font-size: 0.82rem;
    opacity: 0.7;
    margin-top: 0.12rem;
}
.wiq-topbar-spacer {
    height: 0.25rem;
}
.wiq-main-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 0 0 1rem 0;
}
.wiq-main-header .wiq-mark {
    width: 2.2rem;
    height: 2.2rem;
    flex: 0 0 auto;
}
.wiq-main-header .wiq-title {
    font-size: 1.8rem;
    line-height: 1;
}
.wiq-main-header .wiq-kicker {
    margin-top: 0.18rem;
}
.wiq-productivity-wrap {
    margin: 0.35rem 0 1rem 0;
}
.wiq-preview {
    border: 1px solid rgba(120, 120, 120, 0.16);
    border-radius: 16px;
    padding: 0.9rem 1rem;
    background: rgba(255,255,255,0.02);
    margin: 1rem 0 0.8rem 0;
}
.wiq-msg-meta {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
}
.wiq-msg-meta span {
    font-size: 0.7rem;
    padding: 0.18rem 0.5rem;
    border-radius: 999px;
    border: 1px solid rgba(120, 120, 120, 0.22);
    background: rgba(255,255,255,0.03);
}
.wiq-section {
    border-left: 3px solid rgba(120, 120, 120, 0.22);
    padding-left: 0.8rem;
    margin: 0.8rem 0;
}
.wiq-section h4 {
    margin: 0 0 0.3rem 0;
}
.wiq-summary {
    border-left-color: rgba(40, 167, 69, 0.45);
}
.wiq-action {
    border-left-color: rgba(88, 101, 242, 0.55);
}
.wiq-risk {
    border-left-color: rgba(220, 53, 69, 0.5);
}
[data-testid="stButton"] button {
    border-radius: 14px;
}
.wiq-productivity-wrap [data-testid="stButton"] button {
    min-height: 3.2rem;
    font-weight: 600;
    font-size: 1rem;
}
</style>
"""


@dataclass
class RefineResult:
    ok: bool
    output: str
    error: str = ""
    deployment: str = ""


class AzureLLMRefiner:
    def __init__(self, endpoint: str, deployment: str, api_version: str):
        self.endpoint = endpoint.strip()
        self.deployment = deployment.strip()
        self.api_version = api_version.strip() or "2024-12-01-preview"

    def _build_client(self) -> AzureOpenAI:
        if _AZURE_IMPORT_ERROR:
            raise RuntimeError(
                "Azure OpenAI dependencies are not available. Install 'openai' and 'azure-identity'. "
                f"Import error: {_AZURE_IMPORT_ERROR}"
            )
        if not self.endpoint:
            raise RuntimeError("Azure OpenAI endpoint is empty.")
        if not self.deployment:
            raise RuntimeError("Azure OpenAI deployment name is empty.")

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )
        return AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            azure_ad_token_provider=token_provider,
        )

    @staticmethod
    def _coerce_content(message_content: Any) -> str:
        if isinstance(message_content, str):
            return message_content
        if isinstance(message_content, list):
            parts: list[str] = []
            for item in message_content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                else:
                    text = getattr(item, "text", None)
                    if text:
                        parts.append(str(text))
            return "\n".join(parts).strip()
        return str(message_content or "").strip()

    def _style_guide(self, label: str) -> str:
        guides = {
            "Meeting Load Radar": textwrap.dedent(
                """
                Preferred shape:
                ## Executive take
                ## Meeting load snapshot
                ## What to cut or challenge
                ## Time won back
                Keep it tough-minded and quantified where possible.
                """
            ).strip(),
            "Channel Pulse": textwrap.dedent(
                """
                Preferred shape:
                ## What matters now
                ## Decisions made
                ## Action items needing you
                ## Today
                Compress fast and surface only material signal.
                """
            ).strip(),
            "Org Lens": textwrap.dedent(
                """
                Preferred shape:
                ## Org view
                ## Key influencers
                ## Alignment risks
                ## Best outreach moves
                Keep it politically astute and practical.
                """
            ).strip(),
            "Tomorrow Command Center": textwrap.dedent(
                """
                Preferred shape:
                ## Executive call
                ## Critical meetings
                ## Stakeholder readout
                ## Collisions and risks
                ## Tonight's three moves
                Read like a chief-of-staff note.
                """
            ).strip(),
            "Continue From Earlier": textwrap.dedent(
                """
                Preferred shape:
                ## Carried forward
                ## What changed
                ## Highest-value follow-ups
                ## Fastest unblock
                ## Next 24 hours
                Preserve continuity.
                """
            ).strip(),
            "Draft What I Need": textwrap.dedent(
                """
                Preferred shape:
                ## Draft 1
                ## Draft 2
                ## Draft 3
                Each draft should be concise and sendable.
                """
            ).strip(),
        }
        return guides.get(label, "Keep the output compact, structured, and decisive.")

    def test(self) -> RefineResult:
        try:
            client = self._build_client()
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Reply with OK only."},
                    {"role": "user", "content": "OK"},
                ],
                model=self.deployment,
                max_completion_tokens=20,
            )
            content = self._coerce_content(response.choices[0].message.content)
            return RefineResult(ok=True, output=content or "OK", deployment=self.deployment)
        except Exception as exc:  # pragma: no cover - network/auth surface
            return RefineResult(ok=False, output="", error=str(exc), deployment=self.deployment)

    def refine(
        self,
        *,
        raw_output: str,
        user_request: str,
        lens: str,
        label: str,
        feature: str,
        skill: str,
    ) -> RefineResult:
        raw_output = raw_output.strip()
        if not raw_output:
            return RefineResult(ok=False, output="", error="Raw WorkIQ output was empty.", deployment=self.deployment)

        try:
            client = self._build_client()
            style_guide = self._style_guide(label)
            user_prompt = textwrap.dedent(
                f"""
                Refine the answer below into a sharper executive-ready output.

                Context:
                - Feature: {feature or 'General'}
                - Workflow: {label or 'Custom'}
                - Skill: {skill or 'N/A'}

                Original request:
                {user_request.strip()}

                Working lens:
                {lens.strip() or 'No extra lens.'}

                Output requirements:
                - Make it tighter and more impressive, but keep it grounded
                - Keep only the signal
                - Use crisp markdown headings and bullets
                - Avoid repeating the same idea twice
                - Prefer action, ownership, risk, and next moves over narrative
                - Keep it concise enough for an executive to scan quickly
                - Preserve any useful specifics that already exist

                Style guide:
                {style_guide}

                Raw answer to refine:
                {raw_output}
                """
            ).strip()

            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": REFINER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.deployment,
                max_completion_tokens=1400,
            )
            content = self._coerce_content(response.choices[0].message.content).strip()
            if not content:
                return RefineResult(
                    ok=False,
                    output="",
                    error="Azure OpenAI returned an empty refinement.",
                    deployment=self.deployment,
                )
            return RefineResult(ok=True, output=content, deployment=self.deployment)
        except Exception as exc:  # pragma: no cover - network/auth surface
            return RefineResult(ok=False, output="", error=str(exc), deployment=self.deployment)


def init_state() -> None:
    client = WorkIQClient()

    defaults: dict[str, Any] = {
        "messages": [],
        "use_memory": True,
        "show_prompts": True,
        "pending_request": None,
        "draft_prompt": "",
        "current_lens": "",
        "current_panel": "home",
        "selected_productivity_key": "",
        "last_error": "",
        "connection_status": "",
        "diagnostic_status": "",
        "diagnostic_output": "",
        "llm_refiner_enabled": False,
        "llm_status": "",
        "llm_last_error": "",
        "llm_endpoint": os.getenv("AZURE_OPENAI_REFINER_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT", "")).strip(),
        "llm_deployment": os.getenv("AZURE_OPENAI_REFINER_DEPLOYMENT", "gpt-5-mini").strip(),
        "llm_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview").strip(),
    }

    if "cli_command" not in st.session_state:
        default_command = client.default_command().strip()
        st.session_state.cli_command = default_command or "workiq ask"
    if "cli_input_mode" not in st.session_state:
        st.session_state.cli_input_mode = "auto"

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_chat() -> None:
    st.session_state.messages = []
    st.session_state.pending_request = None
    st.session_state.draft_prompt = ""
    st.session_state.current_lens = ""
    st.session_state.last_error = ""
    st.session_state.current_panel = "home"
    st.session_state.selected_productivity_key = ""


def queue_request(item: dict[str, Any]) -> None:
    st.session_state.pending_request = {
        "text": item["prompt"],
        "display_text": item["display_text"],
        "lens": item["lens"],
        "label": item["label"],
        "feature": item["feature"],
        "skill": item.get("skill", ""),
    }
    st.session_state.draft_prompt = item["prompt"]
    st.session_state.current_lens = f"{item['feature']} - {item['label']}"


def activate_top_quick_start(key: str) -> None:
    item = TOP_QUICK_STARTS[key]
    if item.get("opens_panel"):
        st.session_state.current_panel = "productivity"
        st.session_state.current_lens = "Productivity"
        st.session_state.pending_request = None
        st.session_state.draft_prompt = ""
        return

    st.session_state.current_panel = "home"
    queue_request(item)


def activate_productivity_scenario(key: str) -> None:
    st.session_state.current_panel = "productivity"
    st.session_state.selected_productivity_key = key
    queue_request(PRODUCTIVITY_SCENARIOS[key])


def clean_markdown(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("\ufeff", "").replace("\x00", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    replacements = {
        "â€“": "-",
        "â€”": "-",
        "â€˜": "'",
        "â€™": "'",
        'â€œ': '"',
        'â€\x9d': '"',
        "•": "- ",
        "◦": "- ",
    }
    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)

    fixed_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.rstrip()
        if re.match(r"^\?\?\s+[A-Za-z]", line):
            line = "## " + line[3:].strip()
        line = re.sub(r"^[�\?]{2,}\s+(?=[A-Za-z])", "## ", line)
        fixed_lines.append(line)

    cleaned = "\n".join(fixed_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def build_prompt(user_text: str, lens: str = "", memory_context: str = "") -> str:
    parts = [SYSTEM_PROMPT]

    if lens.strip():
        parts.append("Use this working lens:")
        parts.append(lens.strip())

    if memory_context.strip():
        parts.append("Recent context from this session:")
        parts.append(memory_context.strip())

    parts.append("User request:")
    parts.append(user_text.strip())
    return "\n\n".join(parts)


def build_refiner() -> AzureLLMRefiner:
    return AzureLLMRefiner(
        endpoint=st.session_state.llm_endpoint,
        deployment=st.session_state.llm_deployment,
        api_version=st.session_state.llm_api_version,
    )


def run_live_diagnostic(client: WorkIQClient) -> None:
    command = st.session_state.cli_command.strip() or None
    selected_mode = st.session_state.cli_input_mode
    input_mode = None if selected_mode == "auto" else selected_mode

    result = client.run(
        prompt="Reply with one line only: OK",
        command=command,
        input_mode=input_mode,
    )

    if result.ok:
        st.session_state.diagnostic_status = (
            f"Live diagnostic succeeded - command={result.command} mode={result.input_mode}"
        )
        st.session_state.diagnostic_output = result.output.strip()
        st.session_state.last_error = ""
    else:
        st.session_state.diagnostic_status = "Live diagnostic failed."
        st.session_state.diagnostic_output = ""
        st.session_state.last_error = result.error or "Unknown WorkIQ error."


def run_llm_diagnostic() -> None:
    result = build_refiner().test()
    if result.ok:
        st.session_state.llm_status = f"LLM check succeeded - deployment={result.deployment}"
        st.session_state.llm_last_error = ""
    else:
        st.session_state.llm_status = "LLM check failed."
        st.session_state.llm_last_error = result.error or "Unknown Azure OpenAI error."


def render_sidebar(client: WorkIQClient, memory: MemoryManager) -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="wiq-sidebar-brand">
                <div class="wiq-mark">W</div>
                <div>
                    <div class="wiq-title">WorkIQ</div>
                    <div class="wiq-kicker">Showcase</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("Quick starts")

        for key in [
            "workiq_command_center",
            "memory_continue",
            "skills_draft",
            "productivity_hub",
        ]:
            item = TOP_QUICK_STARTS[key]
            st.button(
                item["label"],
                key=f"quick_{key}",
                use_container_width=True,
                on_click=activate_top_quick_start,
                args=(key,),
            )
            st.caption(item["hint"])

        st.divider()
        st.toggle("Memory", key="use_memory")
        st.toggle("Show prompt cards", key="show_prompts")
        st.toggle("Use LLM polish", key="llm_refiner_enabled", help="Run Azure OpenAI as a second-pass refiner after WorkIQ returns.")

        if st.session_state.llm_refiner_enabled:
            with st.expander("LLM polish", expanded=False):
                st.caption("Azure OpenAI via Microsoft Entra ID")
                st.text_input(
                    "Azure OpenAI endpoint",
                    key="llm_endpoint",
                    placeholder="https://your-resource.openai.azure.com/",
                )
                st.text_input(
                    "Deployment name",
                    key="llm_deployment",
                    placeholder="gpt-5-mini",
                )
                st.text_input(
                    "API version",
                    key="llm_api_version",
                    placeholder="2024-12-01-preview",
                )
                if st.button("Test LLM", use_container_width=True):
                    run_llm_diagnostic()
                if st.session_state.llm_status:
                    st.caption(st.session_state.llm_status)
                if st.session_state.llm_last_error:
                    st.code(st.session_state.llm_last_error, language="text")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("New chat", use_container_width=True):
                reset_chat()
                st.rerun()
        with col2:
            if st.button("Clear memory", use_container_width=True):
                memory.clear()
                st.rerun()

        with st.expander("Connection", expanded=False):
            st.text_input(
                "CLI command",
                key="cli_command",
                placeholder="Example: workiq ask",
            )
            st.selectbox(
                "CLI input mode",
                options=["auto", "stdin", "arg"],
                key="cli_input_mode",
                help="Auto lets the client try both stdin and arg.",
            )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Test executable", use_container_width=True):
                    command = st.session_state.cli_command.strip() or None
                    check = client.healthcheck(command=command)
                    if check.ok:
                        detail = check.resolved_executable or check.command
                        st.session_state.connection_status = f"Found executable: {detail}."
                    else:
                        st.session_state.connection_status = check.error
            with col_b:
                if st.button("Run live diagnostic", use_container_width=True):
                    run_live_diagnostic(client)

            if st.session_state.connection_status:
                st.caption(st.session_state.connection_status)
            if st.session_state.diagnostic_status:
                st.caption(st.session_state.diagnostic_status)
            if st.session_state.diagnostic_output:
                st.text_area(
                    "Diagnostic output",
                    value=st.session_state.diagnostic_output,
                    height=90,
                    disabled=True,
                )
            if st.session_state.last_error:
                with st.expander("Last error", expanded=False):
                    st.code(st.session_state.last_error, language="text")


def render_header() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown('<div class="wiq-topbar-spacer"></div>', unsafe_allow_html=True)

    left, right = st.columns([0.16, 0.84])
    with left:
        st.markdown('<div class="wiq-mark">W</div>', unsafe_allow_html=True)
    with right:
        st.markdown(
            """
            <div class="wiq-main-header">
                <div>
                    <div class="wiq-title">WorkIQ</div>
                    <div class="wiq-kicker">Showcase</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_productivity_hub() -> None:
    st.markdown('<div class="wiq-productivity-wrap"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button(
            "Meeting Load Radar",
            key="prod_meeting_load_radar",
            use_container_width=True,
            on_click=activate_productivity_scenario,
            args=("meeting_load_radar",),
        )
    with col2:
        st.button(
            "Channel Pulse",
            key="prod_channel_pulse",
            use_container_width=True,
            on_click=activate_productivity_scenario,
            args=("channel_pulse",),
        )
    with col3:
        st.button(
            "Org Lens",
            key="prod_org_lens",
            use_container_width=True,
            on_click=activate_productivity_scenario,
            args=("org_lens",),
        )


def render_pending_preview() -> bool:
    pending = st.session_state.pending_request
    if not pending:
        return False

    title = pending.get("label", "Prompt") or "Prompt"
    st.markdown(
        f"""
        <div class="wiq-preview">
            <strong>{html.escape(title)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.draft_prompt = st.text_area(
        "Prompt",
        value=st.session_state.draft_prompt or pending.get("text", ""),
        height=240,
        key="draft_prompt_editor",
    )

    col1, col2 = st.columns([1, 1])
    run_now = False
    with col1:
        run_now = st.button("Run", use_container_width=True)
    with col2:
        if st.button("Clear", use_container_width=True):
            st.session_state.pending_request = None
            st.session_state.draft_prompt = ""
            st.rerun()

    if run_now:
        updated = dict(pending)
        updated["text"] = st.session_state.draft_prompt.strip()
        st.session_state.pending_request = updated
        return True

    return False


def parse_sections(markdown_text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    intro_lines: list[str] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in markdown_text.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            elif intro_lines and any(x.strip() for x in intro_lines):
                sections.append(("Overview", "\n".join(intro_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        else:
            if current_title is None:
                intro_lines.append(line)
            else:
                current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    elif intro_lines and any(x.strip() for x in intro_lines):
        sections.append(("Overview", "\n".join(intro_lines).strip()))

    return [(title, body) for title, body in sections if title.strip() or body.strip()]


def classify_section(title: str) -> str:
    lower = title.lower()
    if any(
        k in lower
        for k in [
            "executive",
            "overview",
            "carried forward",
            "critical meetings",
            "org view",
            "cross-channel highlights",
            "meeting load snapshot",
            "what matters now",
            "key influencers",
        ]
    ):
        return "wiq-section wiq-summary"

    if any(
        k in lower
        for k in [
            "tonight",
            "next 24 hours",
            "fastest unblock",
            "draft 1",
            "draft 2",
            "draft 3",
            "delegate",
            "best outreach moves",
            "today",
            "today's response moves",
            "time won back",
            "what to cut",
        ]
    ):
        return "wiq-section wiq-action"

    if any(
        k in lower
        for k in [
            "risk",
            "collisions",
            "urgent",
            "overload",
            "watch-outs",
            "alignment",
        ]
    ):
        return "wiq-section wiq-risk"

    return "wiq-section"


def render_meta_row(feature: str = "", label: str = "", skill: str = "", refined_by: str = "") -> None:
    pills = []
    if feature:
        pills.append(f"<span>{html.escape(feature)}</span>")
    if label:
        pills.append(f"<span>{html.escape(label)}</span>")
    if skill:
        pills.append(f"<span>{html.escape(skill)}</span>")
    if refined_by:
        pills.append(f"<span>polished: {html.escape(refined_by)}</span>")

    if pills:
        st.markdown(
            f'<div class="wiq-msg-meta">{"".join(pills)}</div>',
            unsafe_allow_html=True,
        )


def render_assistant_response(message: dict[str, Any]) -> None:
    render_meta_row(
        feature=message.get("feature", ""),
        label=message.get("label", ""),
        skill=message.get("skill", ""),
        refined_by=message.get("refined_by", ""),
    )

    prompt_used = message.get("prompt", "").strip()
    if st.session_state.show_prompts and prompt_used:
        with st.expander("Prompt used", expanded=False):
            st.code(prompt_used, language="text")
        raw_output = message.get("raw_output", "").strip()
        if raw_output:
            with st.expander("Raw WorkIQ output", expanded=False):
                st.markdown(raw_output)

    sections = parse_sections(message.get("content", ""))
    if not sections:
        st.markdown(message.get("content", ""))
        return

    for title, body in sections:
        css_class = classify_section(title)
        st.markdown(
            f'<div class="{css_class}"><h4>{html.escape(title)}</h4></div>',
            unsafe_allow_html=True,
        )
        if body.strip():
            st.markdown(body)


def render_chat() -> None:
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant"):
                render_assistant_response(msg)
        else:
            with st.chat_message("user"):
                if msg.get("feature") or msg.get("label") or msg.get("skill"):
                    render_meta_row(
                        feature=msg.get("feature", ""),
                        label=msg.get("label", ""),
                        skill=msg.get("skill", ""),
                    )
                st.markdown(msg["content"])


def maybe_refine_output(
    *,
    answer: str,
    request: dict[str, Any],
) -> tuple[str, str, str]:
    if not st.session_state.llm_refiner_enabled:
        return answer, "", ""

    result = build_refiner().refine(
        raw_output=answer,
        user_request=request.get("text", ""),
        lens=request.get("lens", ""),
        label=request.get("label", ""),
        feature=request.get("feature", ""),
        skill=request.get("skill", ""),
    )
    if result.ok:
        st.session_state.llm_status = f"LLM polish succeeded - deployment={result.deployment}"
        st.session_state.llm_last_error = ""
        return clean_markdown(result.output), result.deployment, answer

    st.session_state.llm_status = "LLM polish failed - using raw WorkIQ output."
    st.session_state.llm_last_error = result.error or "Unknown Azure OpenAI error."
    return answer, "", ""


def process_request(request: dict[str, Any], client: WorkIQClient, memory: MemoryManager) -> None:
    user_text = request.get("text", "").strip()
    display_text = request.get("display_text", user_text).strip()
    lens = request.get("lens", "").strip()
    label = request.get("label", "").strip()
    feature = request.get("feature", "").strip()
    skill = request.get("skill", "").strip()

    if not user_text:
        return

    st.session_state.messages.append(
        {
            "role": "user",
            "content": display_text or user_text,
            "feature": feature,
            "label": label,
            "skill": skill,
        }
    )

    memory_context = ""
    if st.session_state.use_memory:
        memory_context = memory.build_context()

    prompt = build_prompt(
        user_text=user_text,
        lens=lens,
        memory_context=memory_context,
    )

    command = st.session_state.cli_command.strip() or None
    selected_mode = st.session_state.cli_input_mode
    input_mode = None if selected_mode == "auto" else selected_mode

    with st.spinner("Working..."):
        result = client.run(
            prompt=prompt,
            command=command,
            input_mode=input_mode,
        )

    if result.ok:
        raw_answer = clean_markdown(result.output)
        answer = raw_answer
        refined_by = ""
        raw_output_for_expander = ""

        if st.session_state.llm_refiner_enabled:
            with st.spinner("Polishing output..."):
                answer, refined_by, raw_output_for_expander = maybe_refine_output(
                    answer=raw_answer,
                    request=request,
                )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "prompt": user_text,
                "feature": feature,
                "label": label,
                "skill": skill,
                "refined_by": refined_by,
                "raw_output": raw_output_for_expander,
            }
        )
        st.session_state.last_error = ""
        st.session_state.diagnostic_status = (
            f"Last run succeeded - command={result.command} mode={result.input_mode}"
        )
        if st.session_state.use_memory:
            memory.remember_turn(
                query=user_text,
                answer=answer,
                workflow=" - ".join(part for part in [feature, label] if part).strip(" -"),
            )
    else:
        st.session_state.last_error = result.error or "Unknown WorkIQ error."
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "I couldn't get a live response from WorkIQ.\n\n"
                    "Open the sidebar and check **Connection** and **Last error**."
                ),
                "prompt": user_text,
                "feature": feature,
                "label": label,
                "skill": skill,
            }
        )

    st.session_state.pending_request = None
    st.session_state.draft_prompt = ""


def main() -> None:
    init_state()
    client = WorkIQClient()
    memory = MemoryManager()

    render_sidebar(client, memory)
    render_header()

    if st.session_state.current_panel == "productivity":
        render_productivity_hub()

    run_pending = render_pending_preview()
    render_chat()

    user_text = st.chat_input(
        "Ask about tomorrow, follow-ups, priorities, drafts, or workload patterns..."
    )
    if user_text:
        st.session_state.pending_request = {
            "text": user_text,
            "display_text": user_text,
            "lens": "",
            "label": "Custom question",
            "feature": "",
            "skill": "",
        }
        process_request(st.session_state.pending_request, client, memory)
        st.rerun()

    if run_pending and st.session_state.pending_request:
        process_request(st.session_state.pending_request, client, memory)
        st.rerun()


if __name__ == "__main__":
    main()
