"""Reusable QThreadPool worker."""

from __future__ import annotations

import traceback
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by a Worker for result, traceback, and completion."""

    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    """Run one callable in a thread pool and expose its lifecycle as signals."""

    def __init__(self, function: Callable, *args, **kwargs):
        """Store a callable and its arguments for execution in QThreadPool."""
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        """Run the callable and report its result, failure, and completion."""
        try:
            result = self.function(*self.args, **self.kwargs)
            self._emit(self.signals.result, result)
        except Exception:  # noqa: BLE001 - worker boundary must report every failure
            self._emit(self.signals.error, traceback.format_exc())
        finally:
            self._emit(self.signals.finished)

    @staticmethod
    def _emit(signal: Signal, *args) -> None:
        """Emit unless Qt already deleted the receiver during application exit."""
        try:
            signal.emit(*args)
        except RuntimeError:
            pass
