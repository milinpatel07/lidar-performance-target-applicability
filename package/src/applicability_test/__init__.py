"""Applicability test of a performance target across conditions for ML-based object detection.

A threshold on an uncertainty indicator is selected with a guarantee in the
condition of selection and tested unchanged in the condition of use; the outcome
is applicable, not applicable, not determined or no threshold selected.
"""
from .core import (APPLICABLE, NO_THRESHOLD, NOT_APPLICABLE, NOT_DETERMINED, ApplicabilityResult,
                   SelectionResult, TestResult, applicability_test, fap, per_unit_shares,
                   quantile_candidates, retention, select_threshold, test_threshold)
from .stats import hb_lower, hb_pvalue, hb_upper, lowest_limit, n_required, zero_failure_bound

__version__ = "0.1.0"

__all__ = [
    "applicability_test", "select_threshold", "test_threshold", "per_unit_shares", "fap", "retention",
    "quantile_candidates", "ApplicabilityResult", "SelectionResult", "TestResult",
    "APPLICABLE", "NOT_APPLICABLE", "NOT_DETERMINED", "NO_THRESHOLD",
    "hb_pvalue", "hb_upper", "hb_lower", "n_required", "zero_failure_bound", "lowest_limit",
]
