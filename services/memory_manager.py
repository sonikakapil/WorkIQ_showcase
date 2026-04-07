from __future__ import annotations

import json
import time
from pathlib import Path


class MemoryManager:
    def __init__(self, path: str = ".workiq_memory.json", max_turns: int = 8):
        self.path = Path(path)
        self.max_turns = max_turns
        self.state = {"turns": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.state = {"turns": []}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def remember_turn(self, query: str, answer: str, workflow: str = "") -> None:
        query = query.strip()
        answer = answer.strip()

        if not query or not answer:
            return

        record = {
            "workflow": workflow.strip(),
            "query": query,
            "answer_summary": self._summarize_answer(answer),
            "ts": time.time(),
        }

        turns = self.state.get("turns", [])
        turns.insert(0, record)
        self.state["turns"] = turns[: self.max_turns]
        self._save()

    def build_context(self, max_turns: int = 3) -> str:
        recent_turns = self.state.get("turns", [])[:max_turns]
        if not recent_turns:
            return ""

        lines = []
        for turn in recent_turns:
            workflow = turn.get("workflow", "").strip()
            query = turn.get("query", "").strip()
            answer_summary = turn.get("answer_summary", "").strip()

            if workflow:
                lines.append(f"- Workflow: {workflow}")
            lines.append(f"  Query: {query}")
            lines.append(f"  Outcome: {answer_summary}")

        return "\n".join(lines).strip()

    def clear(self) -> None:
        self.state = {"turns": []}
        self._save()

    @staticmethod
    def _summarize_answer(answer: str, max_len: int = 700) -> str:
        lines = [line.strip() for line in answer.splitlines() if line.strip()]
        summary = " | ".join(lines[:4])
        return summary[:max_len].strip()