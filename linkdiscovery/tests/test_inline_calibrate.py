"""Hand-computed calibration math: temperature scaling, ECE, conformal rejection."""

from __future__ import annotations

import math

import numpy as np
import pytest

from linkdiscovery.inline import (
    ConformalAbstainer,
    apply_temperature,
    expected_calibration_error,
    fit_temperature,
    reliability_table,
)
from linkdiscovery.inline.calibrate import TEMPERATURE_MAX, TEMPERATURE_MIN


def overconfident_set() -> tuple[np.ndarray, np.ndarray]:
    """A symmetric miscalibrated set: |logit| = 4 (p = 0.982) but 75% accuracy.

    Four confident-positive predictions (one wrong) and the mirror image on
    the negative side. The NLL-optimal temperature satisfies
    sigmoid(4 / T) = 0.75, so T* = 4 / ln(3) ~= 3.641.
    """
    logits = np.array([4.0, 4.0, 4.0, 4.0, -4.0, -4.0, -4.0, -4.0])
    labels = np.array([True, True, True, False, False, False, False, True])
    return logits, labels


def nll(logits: np.ndarray, labels: np.ndarray, temperature: float) -> float:
    """Reference binary NLL used to verify the fitted optimum independently."""
    probs = 1.0 / (1.0 + np.exp(-logits / temperature))
    return float(-np.mean(np.where(labels, np.log(probs), np.log(1.0 - probs))))


class TestFitTemperature:
    def test_recovers_softening_temperature_above_one(self) -> None:
        logits, labels = overconfident_set()
        fitted = fit_temperature(logits, labels)
        # Analytic optimum: sigmoid(4/T) = 0.75 -> T = 4 / ln 3.
        assert fitted == pytest.approx(4.0 / math.log(3.0), abs=1e-3)
        assert fitted > 1.0

    def test_nll_at_fit_is_no_worse_than_identity(self) -> None:
        logits, labels = overconfident_set()
        fitted = fit_temperature(logits, labels)
        assert nll(logits, labels, fitted) <= nll(logits, labels, 1.0)
        # And matches the analytic minimum -(0.75 ln 0.75 + 0.25 ln 0.25).
        expected = -(0.75 * math.log(0.75) + 0.25 * math.log(0.25))
        assert nll(logits, labels, fitted) == pytest.approx(expected, abs=1e-6)

    def test_argmax_is_preserved(self) -> None:
        logits, labels = overconfident_set()
        fitted = fit_temperature(logits, labels)
        before = apply_temperature(logits, 1.0) >= 0.5
        after = apply_temperature(logits, fitted) >= 0.5
        assert np.array_equal(before, after)

    def test_already_calibrated_stays_near_one(self) -> None:
        # sigmoid(ln 3) = 0.75 with 75% accuracy is already calibrated.
        logits = np.array([math.log(3.0)] * 4 + [-math.log(3.0)] * 4)
        labels = np.array([True, True, True, False, False, False, False, True])
        assert fit_temperature(logits, labels) == pytest.approx(1.0, abs=1e-3)
        assert nll(logits, labels, fit_temperature(logits, labels)) <= nll(logits, labels, 1.0)

    def test_stays_inside_search_bounds(self) -> None:
        logits, labels = overconfident_set()
        fitted = fit_temperature(logits, labels)
        assert TEMPERATURE_MIN <= fitted <= TEMPERATURE_MAX

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            fit_temperature(np.array([]), np.array([], dtype=bool))

    def test_all_one_class_raises(self) -> None:
        with pytest.raises(ValueError, match="all one class"):
            fit_temperature(np.array([1.0, 2.0]), np.array([True, True]))
        with pytest.raises(ValueError, match="all one class"):
            fit_temperature(np.array([1.0, 2.0]), np.array([False, False]))

    def test_mismatched_lengths_raise(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            fit_temperature(np.array([1.0, 2.0]), np.array([True]))

    def test_non_finite_logits_raise(self) -> None:
        with pytest.raises(ValueError, match="NaN or infinite"):
            fit_temperature(np.array([1.0, np.nan]), np.array([True, False]))

    def test_non_boolean_labels_raise(self) -> None:
        with pytest.raises(ValueError, match="boolean"):
            fit_temperature(np.array([1.0, -1.0]), np.array([1.0, 0.0]))

    def test_bad_max_iter_raises(self) -> None:
        logits, labels = overconfident_set()
        with pytest.raises(ValueError, match="max_iter"):
            fit_temperature(logits, labels, max_iter=0)


class TestApplyTemperature:
    def test_hand_computed_probabilities(self) -> None:
        probs = apply_temperature(np.array([0.0, math.log(3.0), -math.log(3.0)]), 1.0)
        assert probs == pytest.approx([0.5, 0.75, 0.25])

    def test_temperature_two_halves_the_logit(self) -> None:
        probs = apply_temperature(np.array([2.0 * math.log(3.0)]), 2.0)
        assert probs == pytest.approx([0.75])

    def test_extreme_logits_do_not_overflow(self) -> None:
        probs = apply_temperature(np.array([1000.0, -1000.0]), 1.0)
        assert probs == pytest.approx([1.0, 0.0])

    @pytest.mark.parametrize("temperature", [0.0, -1.0, math.inf, math.nan])
    def test_invalid_temperature_raises(self, temperature: float) -> None:
        with pytest.raises(ValueError, match="temperature"):
            apply_temperature(np.array([1.0]), temperature)

    def test_empty_logits_raise(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            apply_temperature(np.array([]), 1.0)


class TestExpectedCalibrationError:
    def test_hand_built_two_bin_case(self) -> None:
        # Bin [0, .5): probs .2, .3 -> conf .25, acc .5, weight .5 -> .125.
        # Bin [.5, 1]: probs .8, .9 -> conf .85, acc 1., weight .5 -> .075.
        probs = np.array([0.2, 0.3, 0.8, 0.9])
        labels = np.array([False, True, True, True])
        assert expected_calibration_error(probs, labels, bins=2) == pytest.approx(0.2)

    def test_perfectly_calibrated_bin_scores_zero(self) -> None:
        probs = np.array([0.5, 0.5])
        labels = np.array([True, False])
        assert expected_calibration_error(probs, labels, bins=1) == pytest.approx(0.0)

    def test_probability_one_lands_in_last_bin(self) -> None:
        probs = np.array([1.0])
        labels = np.array([True])
        assert expected_calibration_error(probs, labels, bins=10) == pytest.approx(0.0)

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            expected_calibration_error(np.array([]), np.array([], dtype=bool))

    def test_out_of_range_probs_raise(self) -> None:
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            expected_calibration_error(np.array([1.2]), np.array([True]))

    def test_bad_bins_raise(self) -> None:
        with pytest.raises(ValueError, match="bins"):
            expected_calibration_error(np.array([0.5]), np.array([True]), bins=0)


class TestReliabilityTable:
    def test_rows_match_the_ece_hand_case(self) -> None:
        probs = np.array([0.2, 0.3, 0.8, 0.9])
        labels = np.array([False, True, True, True])
        rows = reliability_table(probs, labels, 2)
        assert rows == [
            {
                "bin_lower": 0.0,
                "bin_upper": 0.5,
                "count": 2.0,
                "mean_probability": pytest.approx(0.25),
                "fraction_positive": pytest.approx(0.5),
                "gap": pytest.approx(0.25),
            },
            {
                "bin_lower": 0.5,
                "bin_upper": 1.0,
                "count": 2.0,
                "mean_probability": pytest.approx(0.85),
                "fraction_positive": pytest.approx(1.0),
                "gap": pytest.approx(0.15),
            },
        ]

    def test_empty_bins_are_reported_with_zero_count(self) -> None:
        rows = reliability_table(np.array([0.9]), np.array([True]), 2)
        assert rows[0] == {
            "bin_lower": 0.0,
            "bin_upper": 0.5,
            "count": 0.0,
            "mean_probability": 0.0,
            "fraction_positive": 0.0,
            "gap": 0.0,
        }
        assert rows[1]["count"] == 1.0

    def test_degenerate_input_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            reliability_table(np.array([]), np.array([], dtype=bool), 2)


class TestConformalAbstainer:
    def ten_point_set(self) -> tuple[np.ndarray, np.ndarray]:
        """Ten calibration items with errors at scores 0.2, 0.5, and 0.9."""
        scores = np.array([0.1 * i for i in range(1, 11)])
        correct = np.array([s not in (2, 5, 9) for s in range(1, 11)])
        return scores, correct

    def test_exact_quantile_on_ten_points(self) -> None:
        # n = 10, target_error = 0.2 -> rank = ceil(11 * 0.8) = 9.
        # Alphas sorted: seven -inf (correct items) then 0.2, 0.5, 0.9;
        # the 9th smallest is 0.5, so the threshold is exactly 0.5.
        scores, correct = self.ten_point_set()
        abstainer = ConformalAbstainer().fit(scores, correct, target_error=0.2)
        assert abstainer.threshold == pytest.approx(0.5)
        # Acceptance is strict, so the error at exactly 0.5 is rejected.
        assert not abstainer.accepts(0.5)
        assert abstainer.accepts(0.51)
        # One calibration error (0.9) sits above the threshold:
        # bound (1 + 1) / (10 + 1) = 2/11 <= 0.2 holds.
        assert sum(1 for s, ok in zip(scores, correct, strict=True) if not ok and s > 0.5) == 1

    def test_tighter_error_moves_threshold_up(self) -> None:
        # target_error = 0.1 -> rank = ceil(11 * 0.9) = 10 -> 10th smallest = 0.9.
        scores, correct = self.ten_point_set()
        abstainer = ConformalAbstainer().fit(scores, correct, target_error=0.1)
        assert abstainer.threshold == pytest.approx(0.9)
        assert not abstainer.accepts(0.9)
        assert abstainer.accepts(1.0)

    def test_no_errors_accepts_everything(self) -> None:
        scores = np.array([0.1, 0.2, 0.3])
        abstainer = ConformalAbstainer().fit(scores, np.array([True, True, True]), target_error=0.5)
        assert abstainer.threshold == -math.inf
        assert abstainer.accepts(0.0)

    def test_target_error_below_conformal_floor_raises(self) -> None:
        # 1 / (n + 1) = 1/4; no distribution-free rule can certify 0.1.
        scores = np.array([0.1, 0.2, 0.3])
        correct = np.array([True, False, True])
        with pytest.raises(ValueError, match="distribution-free floor"):
            ConformalAbstainer().fit(scores, correct, target_error=0.1)

    @pytest.mark.parametrize("target_error", [0.0, 1.0, -0.5])
    def test_target_error_out_of_range_raises(self, target_error: float) -> None:
        with pytest.raises(ValueError, match="target_error"):
            ConformalAbstainer().fit(np.array([0.5]), np.array([True]), target_error=target_error)

    def test_empty_calibration_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            ConformalAbstainer().fit(np.array([]), np.array([], dtype=bool), target_error=0.2)

    def test_unfitted_use_raises(self) -> None:
        with pytest.raises(ValueError, match="not fitted"):
            _ = ConformalAbstainer().threshold
        with pytest.raises(ValueError, match="not fitted"):
            ConformalAbstainer().accepts(0.5)
        with pytest.raises(ValueError, match="not fitted"):
            ConformalAbstainer().to_dict()

    def test_dict_round_trip(self) -> None:
        scores, correct = self.ten_point_set()
        fitted = ConformalAbstainer().fit(scores, correct, target_error=0.2)
        restored = ConformalAbstainer.from_dict(fitted.to_dict())
        assert restored.threshold == fitted.threshold
        assert restored.to_dict() == fitted.to_dict()

    def test_infinite_threshold_round_trips_via_null(self) -> None:
        fitted = ConformalAbstainer().fit(
            np.array([0.1, 0.2]), np.array([True, True]), target_error=0.5
        )
        data = fitted.to_dict()
        assert data["threshold"] is None
        restored = ConformalAbstainer.from_dict(data)
        assert restored.threshold == -math.inf
        assert restored.accepts(0.0)

    def test_from_dict_rejects_bad_payloads(self) -> None:
        with pytest.raises(ValueError, match="target_error"):
            ConformalAbstainer.from_dict({"threshold": 0.5})
        with pytest.raises(ValueError, match="n_calibration"):
            ConformalAbstainer.from_dict(
                {"threshold": 0.5, "target_error": 0.2, "n_calibration": -1, "n_errors": 0}
            )
