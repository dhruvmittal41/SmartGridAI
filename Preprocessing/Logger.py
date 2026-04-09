import sys
from datetime import datetime


_R = "\033[91m"
_G = "\033[92m"
_Y = "\033[93m"
_B = "\033[94m"
_W = "\033[0m"
_BOLD = "\033[1m"


def _c(color, text):
    return f"{color}{text}{W}" if sys.stdout.isatty() else text


W = _W  # reset


class StepLogger:
    """Prints structured, colour-coded progress with error trapping."""

    def __init__(self, total_steps: int):
        self.total = total_steps
        self.current = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._start = datetime.now()

    def step(self, name: str):
        self.current += 1
        label = f"[{self.current}/{self.total}]"
        print(f"\n{_BOLD}{_B}{label}{W} {_BOLD}{name}{W}")
        print("─" * 60)

    def ok(self, msg: str):
        print(f"  {_G}✓{W}  {msg}")

    def info(self, msg: str):
        print(f"  {_B}·{W}  {msg}")

    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  {_Y}⚠{W}  {msg}")

    def error(self, msg: str, fatal: bool = False):
        self.errors.append(msg)
        print(f"  {_R}✗{W}  {msg}")
        if fatal:
            self.summary()
            sys.exit(1)

    def section(self, msg: str):
        print(f"\n  {_BOLD}{msg}{W}")

    def summary(self):
        elapsed = (datetime.now() - self._start).seconds
        print("\n" + "═" * 60)
        print(f"{_BOLD}  PREPROCESSING SUMMARY  ({elapsed}s){W}")
        print("═" * 60)
        if self.errors:
            print(f"  {_R}ERRORS ({len(self.errors)}):{W}")
            for e in self.errors:
                print(f"    • {e}")
        if self.warnings:
            print(f"  {_Y}WARNINGS ({len(self.warnings)}):{W}")
            for w in self.warnings:
                print(f"    • {w}")
        if not self.errors:
            print(f"  {_G}All steps completed successfully.{W}")

log = StepLogger(total_steps=10) 
