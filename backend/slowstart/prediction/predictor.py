"""The step predictor behind a small interface, so tests run on a fake and never load a model (R9.2).

The real one is TabPFN v2 (Apache 2.0 weights, R9.1). Newer TabPFN weights (2.5 and later) carry a
non-commercial licence, so the version is pinned here and nowhere else.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Sequence
from typing import Protocol

import numpy as np


class Predictor(Protocol):
    name: str

    def quantiles(
        self, x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, qs: Sequence[float]
    ) -> np.ndarray:
        """Return an array of shape (len(qs), len(x_test))."""
        ...


class TabPFNPredictor:
    """TabPFN v2 on CPU. The weights are loaded once; `fit` only stores the context, so a call is
    one forward pass over (training rows + test rows). Calls are serialised with a lock."""

    name = "tabpfn-v2"

    def __init__(self, n_estimators: int = 4) -> None:
        self.n_estimators = n_estimators
        self._reg = None
        self._lock = threading.Lock()

    def _load(self):
        # The pooled training set passes TabPFN's 1,000-row CPU guard; that size is still small.
        os.environ.setdefault("TABPFN_ALLOW_CPU_LARGE_DATASET", "1")
        from tabpfn import TabPFNRegressor
        from tabpfn.constants import ModelVersion

        self._reg = TabPFNRegressor.create_default_for_version(
            ModelVersion.V2, device="cpu", n_estimators=self.n_estimators
        )

    def warm(self) -> None:
        with self._lock:
            if self._reg is None:
                self._load()

    def quantiles(self, x_train, y_train, x_test, qs):
        with self._lock:
            if self._reg is None:
                self._load()
            self._reg.fit(np.asarray(x_train, dtype=float), np.asarray(y_train, dtype=float))
            out = self._reg.predict(
                np.asarray(x_test, dtype=float), output_type="quantiles", quantiles=list(qs)
            )
        return np.asarray(out, dtype=float)


class EmpiricalPredictor:
    """A stand-in that ignores the features and returns the training targets' quantiles. Used by tests
    and by the app when `SS_USE_TABPFN=false`."""

    name = "empirical"

    def quantiles(self, x_train, y_train, x_test, qs):
        row = np.quantile(np.asarray(y_train, dtype=float), list(qs))
        return np.repeat(row[:, None], len(x_test), axis=1)
