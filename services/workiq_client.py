from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable

from dotenv import load_dotenv


@dataclass
class WorkIQResult:
    ok: bool
    output: str
    error: str = ""
    command: str = ""
    input_mode: str = ""
    resolved_executable: str = ""


class WorkIQClient:
    """
    Wrapper for the installed WorkIQ CLI.

    Supports:
    - explicit command via WORKIQ_CLI_COMMAND or sidebar override
    - explicit input mode via WORKIQ_INPUT_MODE
    - auto-detection of common executable names if no command is supplied
    - automatic fallback between stdin and arg when input_mode is None or "auto"
    """

    COMMON_COMMANDS = [
        "workiq ask",
        "workiq.cmd ask",
        "workiq",
        "workiq.cmd",
        "workiq-cli ask",
        "workiq-cli",
        "wiq ask",
        "wiq",
    ]

    def __init__(self, timeout: int | None = None):
        load_dotenv()
        self.timeout = int(timeout or os.getenv("WORKIQ_TIMEOUT_SECONDS", "120"))

    def default_command(self) -> str:
        env_command = os.getenv("WORKIQ_CLI_COMMAND", "").strip()
        if env_command:
            return env_command

        for candidate in self._candidate_commands():
            if self._resolve_executable(candidate):
                return candidate

        return ""

    def default_input_mode(self) -> str:
        mode = os.getenv("WORKIQ_INPUT_MODE", "auto").strip().lower()
        return mode if mode in {"auto", "stdin", "arg"} else "auto"

    def healthcheck(self, command: str | None = None) -> WorkIQResult:
        commands = [command] if command else list(self._candidate_commands())

        for cmd in commands:
            if not cmd:
                continue

            resolved = self._resolve_executable(cmd)
            if resolved:
                return WorkIQResult(
                    ok=True,
                    output="",
                    command=cmd,
                    resolved_executable=resolved,
                )

        return WorkIQResult(
            ok=False,
            output="",
            error=(
                "No WorkIQ CLI executable was found on PATH. "
                "Set the exact command in the sidebar or in WORKIQ_CLI_COMMAND."
            ),
        )

    def run(
        self,
        prompt: str,
        command: str | None = None,
        input_mode: str | None = None,
    ) -> WorkIQResult:
        prompt = prompt.strip()
        if not prompt:
            return WorkIQResult(ok=False, output="", error="Prompt was empty.")

        commands = [command] if command else list(self._candidate_commands())

        if input_mode in {"stdin", "arg"}:
            modes = [input_mode]
        else:
            default_mode = self.default_input_mode()
            if default_mode in {"stdin", "arg"}:
                modes = [default_mode, "arg" if default_mode == "stdin" else "stdin"]
            else:
                modes = ["stdin", "arg"]

        errors: list[str] = []

        for cmd in commands:
            if not cmd:
                continue

            resolved = self._resolve_executable(cmd)
            if not resolved:
                errors.append(f"Command not found for Python runtime: {cmd}")
                continue

            for mode in modes:
                result = self._execute(cmd, prompt, mode, resolved)
                if result.ok:
                    return result
                errors.append(f"{cmd} [{mode}] - {result.error}")

        error_message = self._condense_errors(errors)
        return WorkIQResult(
            ok=False,
            output="",
            error=error_message or "Unable to run the WorkIQ CLI.",
        )

    def _candidate_commands(self) -> Iterable[str]:
        seen = set()

        env_command = os.getenv("WORKIQ_CLI_COMMAND", "").strip()
        if env_command:
            seen.add(env_command)
            yield env_command

        for command in self.COMMON_COMMANDS:
            if command not in seen:
                seen.add(command)
                yield command

    def _resolve_executable(self, command: str) -> str | None:
        try:
            args = shlex.split(command, posix=False)
            if not args:
                return None

            executable = args[0]

            if os.path.isabs(executable) and os.path.exists(executable):
                return executable

            return shutil.which(executable)
        except Exception:
            return None

    def _execute(
        self,
        command: str,
        prompt: str,
        input_mode: str,
        resolved_executable: str,
    ) -> WorkIQResult:
        try:
            args = shlex.split(command, posix=False)
            args[0] = resolved_executable

            if input_mode == "arg":
                completed = subprocess.run(
                    [*args, prompt],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                    shell=False,
                )
            else:
                completed = subprocess.run(
                    args,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                    shell=False,
                )

            stdout = self._clean_text(completed.stdout)
            stderr = self._clean_text(completed.stderr)

            if completed.returncode != 0:
                return WorkIQResult(
                    ok=False,
                    output="",
                    error=stderr or stdout or f"CLI exited with code {completed.returncode}.",
                    command=command,
                    input_mode=input_mode,
                    resolved_executable=resolved_executable,
                )

            if not stdout.strip():
                return WorkIQResult(
                    ok=False,
                    output="",
                    error="CLI returned no output.",
                    command=command,
                    input_mode=input_mode,
                    resolved_executable=resolved_executable,
                )

            return WorkIQResult(
                ok=True,
                output=stdout.strip(),
                error=stderr.strip(),
                command=command,
                input_mode=input_mode,
                resolved_executable=resolved_executable,
            )

        except FileNotFoundError:
            return WorkIQResult(
                ok=False,
                output="",
                error=f"Executable not found: {resolved_executable}",
                command=command,
                input_mode=input_mode,
                resolved_executable=resolved_executable,
            )
        except subprocess.TimeoutExpired:
            return WorkIQResult(
                ok=False,
                output="",
                error=f"CLI timed out after {self.timeout} seconds.",
                command=command,
                input_mode=input_mode,
                resolved_executable=resolved_executable,
            )
        except Exception as exc:
            return WorkIQResult(
                ok=False,
                output="",
                error=f"Unexpected CLI error: {exc}",
                command=command,
                input_mode=input_mode,
                resolved_executable=resolved_executable,
            )

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)
        text = text.replace("\ufeff", "").replace("\x00", "")
        return text.strip()

    @staticmethod
    def _condense_errors(errors: list[str]) -> str:
        if not errors:
            return ""

        deduped = []
        seen = set()
        for item in errors:
            if item not in seen:
                seen.add(item)
                deduped.append(item)

        if len(deduped) == 1:
            return deduped[0]

        joined = "\n".join(f"- {item}" for item in deduped[:10])
        return f"WorkIQ CLI attempts failed:\n{joined}"