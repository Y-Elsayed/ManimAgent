import ast
import re
import textwrap
from typing import Dict, Tuple


class SyntaxGuardNode:
    """
    Validates and sanitizes Manim code before execution.
    - Ensures required imports
    - Injects AudioMixin usage (optional) with a robust import shim
    - Rewrites self.play(...) -> self.play_with_audio(...) (optional)
    - Fixes common formatting issues (class boundaries, stray ", buff=..." tuples)
    - Checks bracket balance and nested classes
    - Final AST parse to confirm syntax validity

    sanitize(code) -> {"code": <cleaned_code>, "diagnostics": {...}}
    """

    REQUIRED_IMPORTS = [
        "from manim import *",
        "import numpy as np",
    ]

    def __init__(self, enable_audio_mixin: bool = True, replace_play_calls: bool = True):
        self.enable_audio_mixin = enable_audio_mixin
        self.replace_play_calls = replace_play_calls

    # ----------------------------------------------------------------------
    # Import management
    # ----------------------------------------------------------------------
    def _ensure_imports(self, code: str) -> str:
        existing = set(re.findall(r"^(?:from\s+\S+\s+import\s+.*|import\s+.+)$", code, re.MULTILINE))
        missing = [imp for imp in self.REQUIRED_IMPORTS if imp not in existing]
        if missing:
            code = "\n".join(missing) + "\n\n" + code
        return code

    # ----------------------------------------------------------------------
    # Audio import shim header
    # ----------------------------------------------------------------------
    def _inject_audio_header(self, code: str) -> str:
        if not self.enable_audio_mixin:
            return code

        # Remove any direct "from nodes.audio_mixin import AudioMixin" to avoid conflicts
        code = re.sub(r"^\s*from\s+nodes\.audio_mixin\s+import\s+AudioMixin\s*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"^\s*from\s+audio_mixin\s+import\s+AudioMixin\s*$", "", code, flags=re.MULTILINE)

        header = (
            "try:\n"
            "    from nodes.audio_mixin import AudioMixin\n"
            "except ModuleNotFoundError:\n"
            "    try:\n"
            "        from audio_mixin import AudioMixin\n"
            "    except ModuleNotFoundError:\n"
            "        class AudioMixin:\n"
            "            def play_with_audio(self, *animations, **kwargs):\n"
            "                return self.play(*animations, **kwargs)\n\n"
        )

        # Place header before the first 'from manim import' if present; else prepend
        m = re.search(r"(^\s*from\s+manim\s+import\s+\*.*?$)", code, flags=re.MULTILINE | re.DOTALL)
        if m:
            start = m.start(1)
            return code[:start] + header + code[start:]
        return header + code

    # ----------------------------------------------------------------------
    # Balance checks
    # ----------------------------------------------------------------------
    def _check_balance(self, code: str) -> bool:
        pairs = {"(": ")", "[": "]", "{": "}"}
        stack = []
        for ch in code:
            if ch in pairs:
                stack.append(pairs[ch])
            elif ch in pairs.values():
                if not stack or ch != stack.pop():
                    return False
        return len(stack) == 0

    # ----------------------------------------------------------------------
    # Nested Scene class detection
    # ----------------------------------------------------------------------
    def _check_class_nesting(self, code: str) -> Tuple[bool, str]:
        """
        Returns (ok, offending_class_name_or_empty).
        ok=False if a ClassDef contains another ClassDef directly.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"AST parse failed: {e}"

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for inner in node.body:
                    if isinstance(inner, ast.ClassDef):
                        return False, node.name
        return True, ""

    # ----------------------------------------------------------------------
    # Audio injection helpers
    # ----------------------------------------------------------------------
    def _inject_audio_mixin(self, code: str) -> str:
        if not self.enable_audio_mixin:
            return code

        def repl(m):
            bases = m.group(2)
            if "AudioMixin" in bases:
                return m.group(0)
            if "VoiceoverScene" in bases:
                return m.group(0)
            if "Scene" not in bases:
                return m.group(0)
            return f"class {m.group(1)}(AudioMixin, {bases}):"

        return re.sub(r"class\s+(\w+)\(\s*([^)]+?)\s*\):", repl, code)

    def _inject_play_audio(self, code: str) -> str:
        if not self.replace_play_calls:
            return code
        return re.sub(r"\bself\.play\(", "self.play_with_audio(", code)

    # ----------------------------------------------------------------------
    # Formatting & small auto-fixes
    # ----------------------------------------------------------------------
    def _fix_class_boundaries(self, code: str) -> str:
        code = re.sub(r"(\s*self\.wait\([^)]*\))\s*class", r"\1\n\nclass", code)
        code = re.sub(r"(?<!\n)\n(class\s+\w+\s*\([^)]*\)\s*:)", r"\n\n\1", code)
        return code

    def _sanitize_trailing_buff_tuple(self, code: str) -> str:
        return re.sub(r"\)\s*,\s*buff\s*=\s*[\d.]+\)", ")", code)

    def _auto_fix_braces(self, code: str) -> str:
        open_paren, close_paren = code.count("("), code.count(")")
        diff = open_paren - close_paren
        if diff > 0:
            code += ")" * diff
        elif diff < 0:
            for _ in range(-diff):
                idx = code.rfind(")")
                if idx >= 0:
                    code = code[:idx] + code[idx + 1 :]
        return code

    # ----------------------------------------------------------------------
    # Syntax / analysis
    # ----------------------------------------------------------------------
    def _validate_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _analyze_counts(self, code: str) -> Dict[str, int]:
        scene_count = len(re.findall(r"class\s+\w+Scene\s*\(", code))
        play_count = len(re.findall(r"\bself\.play\(", code)) + len(re.findall(r"\bself\.play_with_audio\(", code))
        wait_count = len(re.findall(r"\bself\.wait\(", code))
        return {"scene_count": scene_count, "play_count": play_count, "wait_count": wait_count}

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def sanitize(self, code: str) -> Dict[str, object]:
        applied = []

        # 0) Audio shim at the very top (so import is always resolved)
        before = code
        code = self._inject_audio_header(code)
        if code != before:
            applied.append("audio_header")

        # 1) Imports
        before = code
        code = self._ensure_imports(code)
        if code != before:
            applied.append("imports")

        # 2) Minor text cleanups
        before = code
        code = self._sanitize_trailing_buff_tuple(code)
        if code != before:
            applied.append("trailing_buff_tuple")
        before = code
        code = self._fix_class_boundaries(code)
        if code != before:
            applied.append("class_boundaries")

        # 3) Audio mixin and play() replacement
        before = code
        code = self._inject_audio_mixin(code)
        if code != before:
            applied.append("audio_mixin")
        before = code
        code = self._inject_play_audio(code)
        if code != before:
            applied.append("play_with_audio")

        # 4) Structure checks and simple brace auto-fix
        balanced = self._check_balance(code)
        if not balanced:
            code = self._auto_fix_braces(code)
            balanced = self._check_balance(code)
            applied.append("brace_auto_fix")

        nested_ok, nested_offender = self._check_class_nesting(code)

        # 5) Final syntax check
        syntax_ok = self._validate_syntax(code)

        diagnostics = {
            "balanced_braces": balanced,
            "nested_classes": not nested_ok,
            "nested_offender": nested_offender,
            "syntax_valid": syntax_ok,
            "audio_enabled": self.enable_audio_mixin,
            "play_rewrite_enabled": self.replace_play_calls,
            "transformations": applied,
            **self._analyze_counts(code),
        }

        return {
            "code": textwrap.dedent(code),
            "diagnostics": diagnostics,
        }
