"""Calibration for the no-link decision: temperature scaling and conformal rejection.

Implements SPEC-INLINE-LINKING §6 (Q23, Q26) and the §10 tuning guidance.
Temperature scaling (Guo et al., ICML 2017) is a single-parameter re-shaping
of raw head logits into calibrated accept probabilities: it "does not change
the most-confident prediction", so ordering (and the binary argmax) is
preserved while the no-link threshold tau becomes a meaningful probability.
:class:`ConformalAbstainer` supplies the spec's stronger option — split
conformal prediction with a reject option — whose distribution-free guarantee
is stated precisely on the class.

Everything here is pure numpy (no torch) over 1-D binary problems: ``logits``
are raw real-valued scores for the positive ("link") class and ``labels`` are
booleans (``True`` = the proposal was correct). All functions raise
``ValueError`` with actionable messages on degenerate inputs (empty arrays,
shape mismatches, non-finite values, or an all-one-class label set where the
statistic is undefined).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "TEMPERATURE_MAX",
    "TEMPERATURE_MIN",
    "ConformalAbstainer",
    "apply_temperature",
    "expected_calibration_error",
    "fit_temperature",
    "reliability_table",
]

TEMPERATURE_MIN = 0.05
"""Lower bound of the temperature search interval."""

TEMPERATURE_MAX = 20.0
"""Upper bound of the temperature search interval."""

_SEARCH_TOLERANCE = 1e-12
"""Golden-section bracket width below which the temperature search stops."""


def _as_1d_floats(values: object, name: str, context: str) -> NDArray[np.float64]:
    """Coerce to a finite 1-D float64 array or raise ``ValueError``."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{context}: {name} must be a 1-D array, got {array.ndim} dimensions")
    if array.size == 0:
        raise ValueError(f"{context}: {name} is empty; provide at least one calibration example")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{context}: {name} contains NaN or infinite values")
    return array


def _as_paired_bools(labels: object, size: int, name: str, context: str) -> NDArray[np.bool_]:
    """Coerce labels to a boolean array paired with a ``size``-long array."""
    array = np.asarray(labels)
    if array.dtype != np.bool_:
        raise ValueError(f"{context}: {name} must be a boolean array, got dtype {array.dtype.name}")
    if array.ndim != 1 or array.size != size:
        raise ValueError(
            f"{context}: {name} must be 1-D with the same length as the scores "
            f"({size}), got shape {array.shape}"
        )
    return array


def _validate_probs(
    probs: object, labels: object, context: str
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """Validate a (probabilities, boolean labels) pair for calibration metrics."""
    probs_arr = _as_1d_floats(probs, "probs", context)
    if np.any(probs_arr < 0.0) or np.any(probs_arr > 1.0):
        raise ValueError(f"{context}: probs must lie in [0, 1]; apply_temperature produces these")
    labels_arr = _as_paired_bools(labels, probs_arr.size, "labels", context)
    return probs_arr, labels_arr


def _binary_nll(
    logits: NDArray[np.float64], labels: NDArray[np.bool_], temperature: float
) -> float:
    """Mean negative log-likelihood of sigmoid(logits / temperature) against labels.

    Uses ``logaddexp`` so extreme logits do not overflow:
    ``-log sigmoid(z) = log(1 + e^-z)`` and ``-log(1 - sigmoid(z)) = log(1 + e^z)``.
    """
    scaled = logits / temperature
    signed = np.where(labels, -scaled, scaled)
    return float(np.mean(np.logaddexp(0.0, signed)))


def fit_temperature(
    logits: NDArray[np.float64], labels: NDArray[np.bool_], *, max_iter: int = 200
) -> float:
    """Fit the temperature-scaling parameter T by held-out NLL (spec §6 Q26).

    Method: golden-section search over the *inverse* temperature
    ``s = 1/T`` on ``[1/TEMPERATURE_MAX, 1/TEMPERATURE_MIN]``. The binary NLL
    is the logistic-regression objective in the single coefficient ``s``
    applied to fixed logits, hence convex (so unimodal) in ``s``, which makes
    golden-section search exact up to the bracketing tolerance; Newton would
    also work but golden section needs no derivatives and cannot overshoot
    the bracket. After the search the candidate is compared against T = 1.0
    and the better of the two is returned, so the documented property
    ``NLL(T*) <= NLL(1.0)`` holds unconditionally.

    Because T > 0 divides every logit by the same positive scalar, the sign
    of each logit — and therefore the argmax / most-confident prediction —
    is unchanged (Guo et al. 2017), only the probability magnitudes move.

    Raises ``ValueError`` for empty or mismatched inputs, non-finite logits,
    ``max_iter < 1``, or an all-one-class label set (with one class the NLL
    is minimized at the search boundary and calibration is meaningless;
    collect held-out judgments of both classes, per the spec's guidance to
    reserve >= 100-150 clean judgments for calibration).
    """
    context = "fit_temperature"
    logits_arr = _as_1d_floats(logits, "logits", context)
    labels_arr = _as_paired_bools(labels, logits_arr.size, "labels", context)
    if max_iter < 1:
        raise ValueError(f"{context}: max_iter must be >= 1, got {max_iter}")
    if bool(labels_arr.all()) or not bool(labels_arr.any()):
        raise ValueError(
            f"{context}: labels are all one class; temperature scaling is undefined "
            "without both correct and incorrect examples in the calibration set"
        )

    def nll_of_inverse(s: float) -> float:
        return _binary_nll(logits_arr, labels_arr, 1.0 / s)

    golden = (math.sqrt(5.0) - 1.0) / 2.0
    low, high = 1.0 / TEMPERATURE_MAX, 1.0 / TEMPERATURE_MIN
    inner_low = high - golden * (high - low)
    inner_high = low + golden * (high - low)
    value_low, value_high = nll_of_inverse(inner_low), nll_of_inverse(inner_high)
    for _ in range(max_iter):
        if value_low <= value_high:
            high, inner_high, value_high = inner_high, inner_low, value_low
            inner_low = high - golden * (high - low)
            value_low = nll_of_inverse(inner_low)
        else:
            low, inner_low, value_low = inner_low, inner_high, value_high
            inner_high = low + golden * (high - low)
            value_high = nll_of_inverse(inner_high)
        if high - low < _SEARCH_TOLERANCE:
            break
    fitted = 1.0 / ((low + high) / 2.0)
    if _binary_nll(logits_arr, labels_arr, fitted) <= _binary_nll(logits_arr, labels_arr, 1.0):
        return float(fitted)
    return 1.0


def apply_temperature(logits: NDArray[np.float64], temperature: float) -> NDArray[np.float64]:
    """Convert raw logits to calibrated probabilities: ``sigmoid(logits / T)``.

    Raises ``ValueError`` on empty or non-finite logits and on a temperature
    outside ``(0, inf)`` (a non-positive temperature would flip or destroy
    the argmax-preservation property that motivates temperature scaling).
    """
    context = "apply_temperature"
    logits_arr = _as_1d_floats(logits, "logits", context)
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError(
            f"{context}: temperature must be a finite positive number, got {temperature!r}"
        )
    scaled = logits_arr / temperature
    # Numerically stable sigmoid: exp(-|z|) never overflows.
    damped = np.exp(-np.abs(scaled))
    result: NDArray[np.float64] = np.where(
        scaled >= 0.0, 1.0 / (1.0 + damped), damped / (1.0 + damped)
    )
    return result


def _bin_indices(probs: NDArray[np.float64], bins: int) -> NDArray[np.int64]:
    """Equal-width bin index in ``[0, bins)`` for each probability; 1.0 joins the last bin."""
    indices: NDArray[np.int64] = np.minimum((probs * bins).astype(np.int64), np.int64(bins - 1))
    return indices


def expected_calibration_error(
    probs: NDArray[np.float64], labels: NDArray[np.bool_], *, bins: int = 10
) -> float:
    """Standard expected calibration error over equal-width probability bins.

    ``ECE = sum_b (n_b / N) * |acc_b - conf_b|`` where, within bin ``b``,
    ``conf_b`` is the mean predicted probability and ``acc_b`` the observed
    positive fraction (the binary-classifier form of Guo et al. 2017, used to
    verify the spec §6 Q26 requirement that calibrated scores track human
    acceptance rates). Empty bins contribute nothing.

    Raises ``ValueError`` for empty inputs, probabilities outside [0, 1],
    mismatched lengths, or ``bins < 1``.
    """
    context = "expected_calibration_error"
    probs_arr, labels_arr = _validate_probs(probs, labels, context)
    if bins < 1:
        raise ValueError(f"{context}: bins must be >= 1, got {bins}")
    indices = _bin_indices(probs_arr, bins)
    total = probs_arr.size
    ece = 0.0
    for bin_index in range(bins):
        mask = indices == bin_index
        count = int(mask.sum())
        if count == 0:
            continue
        confidence = float(probs_arr[mask].mean())
        accuracy = float(labels_arr[mask].mean())
        ece += (count / total) * abs(accuracy - confidence)
    return float(ece)


def reliability_table(
    probs: NDArray[np.float64], labels: NDArray[np.bool_], bins: int = 10
) -> list[dict[str, float]]:
    """Per-bin reliability rows for calibration reporting (spec §6 Q26).

    Each row covers one equal-width bin: ``bin_lower`` / ``bin_upper`` bound
    the bin, ``count`` is the number of items whose probability fell in it,
    ``mean_probability`` and ``fraction_positive`` are the bin's confidence
    and observed accuracy, and ``gap`` is their absolute difference (the
    quantity ECE averages). Empty bins are included with ``count`` 0 and the
    remaining statistics 0.0 so reporters can render a complete diagram.

    Raises ``ValueError`` under the same conditions as
    :func:`expected_calibration_error`.
    """
    context = "reliability_table"
    probs_arr, labels_arr = _validate_probs(probs, labels, context)
    if bins < 1:
        raise ValueError(f"{context}: bins must be >= 1, got {bins}")
    indices = _bin_indices(probs_arr, bins)
    rows: list[dict[str, float]] = []
    for bin_index in range(bins):
        mask = indices == bin_index
        count = int(mask.sum())
        if count:
            confidence = float(probs_arr[mask].mean())
            accuracy = float(labels_arr[mask].mean())
            gap = abs(accuracy - confidence)
        else:
            confidence = accuracy = gap = 0.0
        rows.append(
            {
                "bin_lower": bin_index / bins,
                "bin_upper": (bin_index + 1) / bins,
                "count": float(count),
                "mean_probability": confidence,
                "fraction_positive": accuracy,
                "gap": gap,
            }
        )
    return rows


class ConformalAbstainer:
    """Split-conformal selective prediction with a reject option (spec §6 Q26).

    The spec asks for the Linusson-style reject option: "at most k errors
    among accepted suggestions" without revealing test labels. Fitting takes
    a held-out calibration set of ``scores`` (any monotone confidence score;
    higher = more confident) and ``correct`` flags, and computes the score
    threshold above which items are accepted.

    Exact guarantee implemented (marginal, distribution-free, finite-sample):
    assign each calibration item the nonconformity value ``alpha_i = score_i``
    if it is an error and ``-inf`` if it is correct, and set the threshold to
    the ``ceil((n + 1) * (1 - target_error))``-th smallest of the ``n``
    calibration alphas — the standard split-conformal quantile with the
    ``(n + 1)`` finite-sample correction. For a test item exchangeable with
    the calibration set,

        P(item is accepted AND its prediction is wrong) <= target_error.

    This is a *joint* (marginal) bound over acceptance and error, not a bound
    conditional on acceptance: the error rate among accepted items is bounded
    by ``target_error / P(accept)``. It holds for any score distribution and
    requires no correctly-specified model; it is marginal over calibration
    draws, not conditional on this particular calibration set. Acceptance is
    strict (``score > threshold``) so ties with the threshold value never
    inflate the accepted-error count.
    """

    def __init__(self) -> None:
        self._threshold: float | None = None
        self._target_error: float | None = None
        self._n_calibration: int = 0
        self._n_errors: int = 0

    def fit(
        self,
        scores: NDArray[np.float64],
        correct: NDArray[np.bool_],
        *,
        target_error: float,
    ) -> ConformalAbstainer:
        """Fit the acceptance threshold on a held-out calibration set.

        Raises ``ValueError`` for empty or mismatched inputs, a
        ``target_error`` outside ``(0, 1)``, or a calibration set too small
        for the guarantee: the conformal bound cannot certify a rate below
        ``1 / (n + 1)``, so ``n >= ceil(1 / target_error) - 1`` items are
        required. Returns ``self`` for chaining.
        """
        context = "ConformalAbstainer.fit"
        scores_arr = _as_1d_floats(scores, "scores", context)
        correct_arr = _as_paired_bools(correct, scores_arr.size, "correct", context)
        if not 0.0 < target_error < 1.0:
            raise ValueError(f"{context}: target_error must be in (0, 1), got {target_error!r}")
        n = scores_arr.size
        rank = math.ceil((n + 1) * (1.0 - target_error))
        if rank > n:
            needed = math.ceil(1.0 / target_error) - 1
            raise ValueError(
                f"{context}: target_error={target_error} is below the distribution-free "
                f"floor 1/(n+1) for n={n} calibration items; provide at least "
                f"{needed} items or raise target_error"
            )
        alphas = np.where(correct_arr, -np.inf, scores_arr)
        self._threshold = float(np.sort(alphas)[rank - 1])
        self._target_error = target_error
        self._n_calibration = n
        self._n_errors = int(np.count_nonzero(~correct_arr))
        return self

    @property
    def threshold(self) -> float:
        """The fitted acceptance threshold (``-inf`` means accept everything).

        Raises ``ValueError`` when the abstainer has not been fitted.
        """
        if self._threshold is None:
            raise ValueError("ConformalAbstainer: not fitted; call fit() before threshold")
        return self._threshold

    def accepts(self, score: float) -> bool:
        """Whether an item with this confidence score is accepted (strictly above threshold).

        Raises ``ValueError`` when the abstainer has not been fitted.
        """
        return bool(score > self.threshold)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives (``-inf`` threshold stored as null).

        Raises ``ValueError`` when the abstainer has not been fitted.
        """
        threshold = self.threshold
        return {
            "threshold": threshold if math.isfinite(threshold) else None,
            "target_error": self._target_error,
            "n_calibration": self._n_calibration,
            "n_errors": self._n_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConformalAbstainer:
        """Deserialize a fitted abstainer, raising ``ValueError`` on invalid input."""
        context = "ConformalAbstainer.from_dict"
        if not isinstance(data, dict):
            raise ValueError(f"{context}: expected a dict, got {type(data).__name__}")
        threshold = data.get("threshold")
        if threshold is not None and not isinstance(threshold, int | float):
            raise ValueError(f"{context}: field 'threshold' must be a number or null")
        target_error = data.get("target_error")
        if not isinstance(target_error, int | float) or not 0.0 < float(target_error) < 1.0:
            raise ValueError(f"{context}: field 'target_error' must be a number in (0, 1)")
        n_calibration = data.get("n_calibration")
        n_errors = data.get("n_errors")
        for name, value in (("n_calibration", n_calibration), ("n_errors", n_errors)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{context}: field '{name}' must be a non-negative integer")
        assert isinstance(n_calibration, int) and isinstance(n_errors, int)
        instance = cls()
        instance._threshold = float(threshold) if threshold is not None else -math.inf
        instance._target_error = float(target_error)
        instance._n_calibration = n_calibration
        instance._n_errors = n_errors
        return instance
