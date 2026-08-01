"""Data audit for the inline-link subsystem (SPEC-INLINE-LINKING §4).

The audit is the first, gating deliverable: a stratified sample of existing
links, a terminal annotation tool, inter-annotator agreement statistics, and
the tier-based go/no-go report that decides whether existing links are
usable as weak supervision.
"""

from linkdiscovery.inline.audit.agreement import (
    agreement_report,
    cohen_kappa,
    krippendorff_alpha,
)
from linkdiscovery.inline.audit.annotate import (
    load_audit_labels,
    run_annotation_session,
    save_audit_labels,
)
from linkdiscovery.inline.audit.sampler import build_audit_sample
from linkdiscovery.inline.audit.tiers import (
    GRAPH_ONLY_REGIONS,
    build_audit_report,
    derive_tier,
)

__all__ = [
    "GRAPH_ONLY_REGIONS",
    "agreement_report",
    "build_audit_report",
    "build_audit_sample",
    "cohen_kappa",
    "derive_tier",
    "krippendorff_alpha",
    "load_audit_labels",
    "run_annotation_session",
    "save_audit_labels",
]
