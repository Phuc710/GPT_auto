# step_tracker.py - Smart step progress tracker with visual display

import time
import sys
import os
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


# ============ ANSI COLORS ============
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    @staticmethod
    def supports_color() -> bool:
        """Check if terminal supports ANSI colors."""
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# Enable Windows ANSI support globally
Color.supports_color()


# ============ STEP STATUS ============
class StepStatus(Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    SKIPPED  = "skipped"


# ============ STEP ============
@dataclass
class Step:
    name: str
    label: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    error: Optional[str] = None

    @property
    def elapsed(self) -> Optional[float]:
        if self.started_at is None:
            return None
        end = self.ended_at if self.ended_at else time.time()
        return end - self.started_at

    @property
    def elapsed_str(self) -> str:
        elapsed = self.elapsed
        if elapsed is None:
            return ""
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        return f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

    @property
    def icon(self) -> str:
        icons = {
            StepStatus.PENDING:  " ",
            StepStatus.RUNNING:  "⟳",
            StepStatus.DONE:     "✓",
            StepStatus.FAILED:   "✗",
            StepStatus.SKIPPED:  "-",
        }
        return icons[self.status]

    @property
    def color(self) -> str:
        colors = {
            StepStatus.PENDING:  Color.GRAY,
            StepStatus.RUNNING:  Color.YELLOW,
            StepStatus.DONE:     Color.GREEN,
            StepStatus.FAILED:   Color.RED,
            StepStatus.SKIPPED:  Color.GRAY,
        }
        return colors[self.status]


# ============ STEP TRACKER ============
class StepTracker:
    """
    Visual step tracker with colored status display.

    Usage:
        tracker = StepTracker("Account #1", [
            ("email",    "Tao email tam thoi"),
            ("browser",  "Mo trinh duyet"),
            ("signup",   "Den trang dang ky"),
            ...
        ])
        tracker.start("email")
        tracker.done("email")
        tracker.start("browser")
        tracker.fail("browser", "Timeout")
    """

    WIDTH = 62

    def __init__(self, title: str, steps: list[tuple[str, str]]):
        self.title   = title
        self.steps   = [Step(name=k, label=v) for k, v in steps]
        self._map    = {s.name: s for s in self.steps}
        self._lines  = 0          # Track how many lines we printed (for overwrite)
        self._started_at = time.time()

    # -------- Public API --------

    def start(self, name: str):
        """Mark step as running and redraw."""
        step = self._get(name)
        if step:
            step.status = StepStatus.RUNNING
            step.started_at = time.time()
            self._draw()

    def done(self, name: str):
        """Mark step as done and redraw."""
        step = self._get(name)
        if step:
            step.status = StepStatus.DONE
            step.ended_at = time.time()
            self._draw()

    def fail(self, name: str, reason: str = ""):
        """Mark step as failed and redraw."""
        step = self._get(name)
        if step:
            step.status = StepStatus.FAILED
            step.ended_at = time.time()
            step.error = reason
            self._draw()

    def skip(self, name: str):
        """Mark step as skipped and redraw."""
        step = self._get(name)
        if step:
            step.status = StepStatus.SKIPPED
            step.ended_at = time.time()
            self._draw()

    def summary(self, success: bool, detail: str = ""):
        """Print final result summary."""
        self._draw(final=True)
        total = time.time() - self._started_at

        W = self.WIDTH
        print(f"\n{Color.BOLD}{'=' * W}{Color.RESET}")
        if success:
            print(f"{Color.GREEN}{Color.BOLD}  ✓  THÀNH CÔNG{Color.RESET}")
        else:
            print(f"{Color.RED}{Color.BOLD}  ✗  THẤT BẠI{Color.RESET}")

        if detail:
            print(f"     {detail}")

        # Step summary
        done_count    = sum(1 for s in self.steps if s.status == StepStatus.DONE)
        failed_count  = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        total_steps   = len([s for s in self.steps if s.status != StepStatus.SKIPPED])
        print(f"  {Color.GRAY}Các bước: {done_count}/{total_steps} hoàn thành"
              + (f"  |  {failed_count} lỗi" if failed_count else "")
              + Color.RESET)

        # Failed steps detail
        for s in self.steps:
            if s.status == StepStatus.FAILED and s.error:
                print(f"  {Color.RED}  → {s.label}: {s.error}{Color.RESET}")

        total_str = f"{total:.1f}s" if total < 60 else f"{int(total//60)}p {int(total%60)}giây"
        print(f"  {Color.GRAY}Tổng thời gian: {total_str}{Color.RESET}")
        print(f"{Color.BOLD}{'=' * W}{Color.RESET}\n")

    # -------- Internal --------

    def _get(self, name: str) -> Optional[Step]:
        return self._map.get(name)

    def _clear(self):
        """Move cursor up to overwrite previous output."""
        if self._lines > 0:
            sys.stdout.write(f"\033[{self._lines}A\033[J")
            sys.stdout.flush()

    def _draw(self, final: bool = False):
        """Redraw the full step board."""
        self._clear()

        W   = self.WIDTH
        out = []

        # Minimalist Header
        elapsed = time.time() - self._started_at
        e_str = f"{elapsed:.0f}s"
        title_line = f"  {Color.BOLD}{Color.CYAN}{self.title}{Color.RESET}"
        out.append(f"\n{title_line:<{W}}{Color.GRAY}{e_str:>6}{Color.RESET}")
        out.append(f"{Color.GRAY}{'─' * W}{Color.RESET}")

        # Steps
        for step in self.steps:
            icon_colored = f"{step.color}{Color.BOLD}[{step.icon}]{Color.RESET}"

            label_colored = step.label
            if step.status == StepStatus.RUNNING:
                label_colored = f"{Color.YELLOW}{Color.BOLD}{step.label}{Color.RESET}"
            elif step.status == StepStatus.DONE:
                label_colored = f"{Color.WHITE}{step.label}{Color.RESET}"
            elif step.status == StepStatus.FAILED:
                label_colored = f"{Color.RED}{step.label}{Color.RESET}"
            else:
                label_colored = f"{Color.GRAY}{step.label}{Color.RESET}"

            # Right side info
            if step.status == StepStatus.RUNNING:
                right = f"{Color.YELLOW}running...{Color.RESET}"
            elif step.status in (StepStatus.DONE, StepStatus.FAILED, StepStatus.SKIPPED):
                t = step.elapsed_str
                color = Color.GREEN if step.status == StepStatus.DONE else Color.RED
                right = f"{color}{t}{Color.RESET}"
            else:
                right = ""

            # Visible length calculation
            visible_left = f"  [{step.icon}]  {step.label}"
            pad = W - len(visible_left) - 10
            out.append(f"  {icon_colored}  {label_colored}{' ' * max(pad, 1)}{right}")

            # Show error detail inline
            if step.status == StepStatus.FAILED and step.error:
                out.append(f"       {Color.RED}{Color.DIM}↳ {step.error}{Color.RESET}")

        out.append(f"{Color.GRAY}{'─' * W}{Color.RESET}")

        text = "\n".join(out)
        print(text)
        self._lines = len(out) + 1  # Track lines for next clear


# ============ LOGGER (Pro) ============
class Logger:
    """
    Enhanced logger with colored output and consistent formatting.
    Integrates with StepTracker when provided.
    """

    @staticmethod
    def info(msg: str):
        print(f"  {Color.BLUE}ℹ{Color.RESET}  {msg}")

    @staticmethod
    def success(msg: str):
        print(f"  {Color.GREEN}✓{Color.RESET}  {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"  {Color.YELLOW}⚠{Color.RESET}  {msg}", file=sys.stderr)

    @staticmethod
    def error(msg: str):
        print(f"  {Color.RED}✗{Color.RESET}  {msg}", file=sys.stderr)

    @staticmethod
    def debug(msg: str):
        print(f"  {Color.GRAY}·{Color.RESET}  {Color.DIM}{msg}{Color.RESET}")

    @staticmethod
    def section(title: str):
        W = 62
        print(f"\n{Color.BOLD}{'=' * W}")
        print(f"  {title}")
        print(f"{'=' * W}{Color.RESET}\n")

    @staticmethod
    def sub(msg: str):
        """Chi tiết bước phụ (thụt lề)"""
        print(f"  {Color.GRAY}  → {msg}{Color.RESET}")
