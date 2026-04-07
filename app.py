from __future__ import annotations

import html
import re
import textwrap

import streamlit as st
from dotenv import load_dotenv

from services.memory_manager import MemoryManager
from services.workiq_client import WorkIQClient

load_dotenv()

st.set_page_config(
    page_title="WorkIQ",
    page_icon="W",
    layout="wide",
    initial_sidebar_state="expanded",
)

QUICK_STARTS = {
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
    "productivity_calendar_surgery": {
        "feature": "Productivity",
        "label": "Calendar Surgery",
        "hint": "Show where time is leaking and what to cut, delegate, or protect.",
        "display_text": "Calendar Surgery",
        "prompt": (
            "Act like my executive chief of staff and perform calendar surgery.\n\n"
            "Use my recent work patterns and current commitments.\n\n"
            "Show me:\n"
            "- what is consuming disproportionate time or attention\n"
            "- which threads genuinely deserve my direct involvement\n"
            "- what meetings or work patterns I should stop, shorten, delegate, or move async\n"
            "- where I am personally acting as a bottleneck\n"
            "- 2 focus blocks I should protect this week\n"
            "- the approximate time I could win back\n\n"
            "Be direct and opinionated. Optimize for leverage, not completeness.\n"
            "End with: This week would feel better if..."
        ),
        "lens": textwrap.dedent(
            """
            Shape the answer as a productivity operating review.

            Prefer these section headings:
            ## Executive take
            ## Time leaks
            ## What deserves your time
            ## Meetings to cut or shorten
            ## Delegate or move async
            ## Focus blocks to protect
            ## Time recovered
            ## This week would feel better if

            Be specific and practical.
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
    - Do not use tables unless explicitly asked
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

APP_CSS = """
<style>
    .block-container {
        max-width: 1160px;
        padding-top: 1.6rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stChatMessage"] {
        padding-top: 0.22rem;
        padding-bottom: 0.22rem;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
        font-size: 1rem;
        line-height: 1.62;
    }

    button, div[data-baseweb="button"] > button {
        border-radius: 12px !important;
    }

    .meta-row {
        display: flex;
        gap: 0.45rem;
        flex-wrap: wrap;
        margin-bottom: 0.55rem;
    }

    .meta-pill {
        display: inline-block;
        padding: 0.22rem 0.62rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
    }

    .meta-feature {
        background: rgba(99, 102, 241, 0.18);
        border-color: rgba(99, 102, 241, 0.45);
    }

    .meta-label {
        background: rgba(255,255,255,0.06);
    }

    .prompt-card {
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.03);
        border-radius: 14px;
        padding: 0.35rem 0.75rem 0.1rem 0.75rem;
        margin-bottom: 0.9rem;
    }

    .prompt-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.72;
        margin-bottom: 0.3rem;
    }

    .section-title {
        margin-top: 0.9rem;
        margin-bottom: 0.35rem;
        padding: 0.52rem 0.72rem;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.98rem;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.04);
    }

    .section-summary {
        background: rgba(59, 130, 246, 0.14);
        border-color: rgba(59, 130, 246, 0.35);
    }

    .section-action {
        background: rgba(16, 185, 129, 0.14);
        border-color: rgba(16, 185, 129, 0.35);
    }

    .section-risk {
        background: rgba(245, 158, 11, 0.14);
        border-color: rgba(245, 158, 11, 0.35);
    }

    .section-neutral {
        background: rgba(255,255,255,0.04);
        border-color: rgba(255,255,255,0.10);
    }

    .quickstart-title {
        font-weight: 700;
        margin-bottom: 0.15rem;
    }

    .quickstart-sub {
        font-size: 0.86rem;
        opacity: 0.74;
        margin-bottom: 0.55rem;
    }
</style>
"""


def init_state() -> None:
    client = WorkIQClient()

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Choose a quick start from the sidebar or ask your own question.",
            }
        ]

    if "use_memory" not in st.session_state:
        st.session_state.use_memory = True

    if "show_prompts" not in st.session_state:
        st.session_state.show_prompts = True

    if "pending_request" not in st.session_state:
        st.session_state.pending_request = None

    if "current_lens" not in st.session_state:
        st.session_state.current_lens = ""

    if "last_error" not in st.session_state:
        st.session_state.last_error = ""

    if "cli_command" not in st.session_state:
        st.session_state.cli_command = client.default_command()

    if "cli_input_mode" not in st.session_state:
        st.session_state.cli_input_mode = "auto"

    if "connection_status" not in st.session_state:
        st.session_state.connection_status = ""

    if "diagnostic_status" not in st.session_state:
        st.session_state.diagnostic_status = ""

    if "diagnostic_output" not in st.session_state:
        st.session_state.diagnostic_output = ""


def reset_chat() -> None:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Choose a quick start from the sidebar or ask your own question.",
        }
    ]
    st.session_state.pending_request = None
    st.session_state.current_lens = ""
    st.session_state.last_error = ""


def queue_quick_start(key: str) -> None:
    item = QUICK_STARTS[key]
    st.session_state.pending_request = {
        "text": item["prompt"],
        "display_text": item["display_text"],
        "lens": item["lens"],
        "label": item["label"],
        "feature": item["feature"],
    }
    st.session_state.current_lens = f"{item['feature']} - {item['label']}"


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

    fixed_lines = []
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


def render_sidebar(client: WorkIQClient, memory: MemoryManager) -> None:
    with st.sidebar:
        st.subheader("Quick starts")

        for key in [
            "workiq_command_center",
            "memory_continue",
            "skills_draft",
            "productivity_calendar_surgery",
        ]:
            item = QUICK_STARTS[key]
            st.button(
                f"{item['feature']} - {item['label']}",
                key=f"quick_{key}",
                use_container_width=True,
                on_click=queue_quick_start,
                args=(key,),
            )
            st.caption(item["hint"])

        st.divider()
        st.toggle("Memory", key="use_memory")
        st.toggle("Show prompt cards", key="show_prompts")

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
                        st.session_state.connection_status = (
                            f"Found executable: {detail}."
                        )
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
                st.code(st.session_state.last_error)


def render_header() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.title("WorkIQ")
    st.caption("Turn work context into next actions")

    if st.session_state.current_lens:
        st.caption(f"Current lens: {st.session_state.current_lens}")


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

    if any(k in lower for k in [
        "executive",
        "overview",
        "carried forward",
        "critical meetings",
        "what deserves your time",
    ]):
        return "section-summary"

    if any(k in lower for k in [
        "tonight",
        "next 24 hours",
        "fastest unblock",
        "draft 1",
        "draft 2",
        "draft 3",
        "delegate",
        "focus blocks",
        "time recovered",
        "this week would feel better",
        "decide / delegate / defer",
        "meetings to cut or shorten",
    ]):
        return "section-action"

    if any(k in lower for k in [
        "risk",
        "collisions",
        "time leaks",
        "bottleneck",
        "urgent",
    ]):
        return "section-risk"

    return "section-neutral"


def render_meta_row(feature: str = "", label: str = "") -> None:
    pills = []
    if feature:
        pills.append(f"<span class='meta-pill meta-feature'>{html.escape(feature)}</span>")
    if label:
        pills.append(f"<span class='meta-pill meta-label'>{html.escape(label)}</span>")

    if pills:
        st.markdown(
            f"<div class='meta-row'>{''.join(pills)}</div>",
            unsafe_allow_html=True,
        )


def render_assistant_response(message: dict) -> None:
    render_meta_row(
        feature=message.get("feature", ""),
        label=message.get("label", ""),
    )

    prompt_used = message.get("prompt", "").strip()
    if st.session_state.show_prompts and prompt_used:
        st.markdown("<div class='prompt-card'><div class='prompt-title'>Prompt used</div></div>", unsafe_allow_html=True)
        st.code(prompt_used, language="text")

    sections = parse_sections(message.get("content", ""))
    if not sections:
        st.markdown(message.get("content", ""))
        return

    for title, body in sections:
        css_class = classify_section(title)
        st.markdown(
            f"<div class='section-title {css_class}'>{html.escape(title)}</div>",
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
                if msg.get("feature"):
                    render_meta_row(
                        feature=msg.get("feature", ""),
                        label=msg.get("label", ""),
                    )
                st.markdown(msg["content"])


def process_request(request: dict, client: WorkIQClient, memory: MemoryManager) -> None:
    user_text = request.get("text", "").strip()
    display_text = request.get("display_text", user_text).strip()
    lens = request.get("lens", "").strip()
    label = request.get("label", "").strip()
    feature = request.get("feature", "").strip()

    if not user_text:
        return

    st.session_state.messages.append(
        {
            "role": "user",
            "content": display_text or user_text,
            "feature": feature,
            "label": label,
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
        answer = clean_markdown(result.output)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "prompt": user_text,
                "feature": feature,
                "label": label,
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
                workflow=f"{feature} - {label}".strip(" -"),
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
            }
        )


def main() -> None:
    init_state()

    client = WorkIQClient()
    memory = MemoryManager()

    render_sidebar(client, memory)
    render_header()
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
        }

    pending = st.session_state.pending_request
    if pending:
        st.session_state.pending_request = None
        process_request(pending, client, memory)
        st.rerun()


if __name__ == "__main__":
    main()