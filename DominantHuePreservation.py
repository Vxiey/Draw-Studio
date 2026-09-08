"""Dominant hue preservation for Draw Studio Step 3.

Pure planning helpers used by both source-derived exact colour reduction and
browser/game palette reduction.  The policy protects large chromatic families
before spending palette slots on extra shades or small texture colours.

No UI, mouse, filesystem, network or renderer behaviour lives here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from ColorFidelity import oklab_metrics

RGB = tuple[int, int, int]

# Representative OKLab hue centres.  These are intentionally broader than the
# previous 30-degree bins: neighbouring shades of one semantic colour family
# should share one protected slot instead of competing with each other.
_FAMILY_CENTRES = (
    ("red", 25.0),
    ("orange", 58.0),
    ("yellow", 108.0),
    ("green", 148.0),
    ("cyan", 195.0),
    ("blue", 260.0),
    ("purple", 295.0),
    ("magenta", 330.0),
)


def _rgb(values: Sequence[int | float]) -> RGB:
    vals=list(values[:3])
    while len(vals)<3: vals.append(0)
    return tuple(max(0,min(255,int(round(float(v))))) for v in vals)  # type: ignore[return-value]


def _circular_distance(a: float, b: float) -> float:
    d=abs(float(a)-float(b))%360.0
    return min(d,360.0-d)


def dominant_hue_family(rgb: Sequence[int], *, chroma_threshold: float=4.5) -> str | None:
    """Return a broad OKLab hue family, or None for near-neutral colours."""
    _L,C,H=oklab_metrics(_rgb(rgb))
    if C < float(chroma_threshold):
        return None
    return min(_FAMILY_CENTRES,key=lambda item:(_circular_distance(H,item[1]),item[1]))[0]


@dataclass(frozen=True)
class HueFamilySummary:
    family: str
    weight: float
    coverage: float
    representative_index: int
    representative_rgb: RGB
    representative_chroma: float


def _coverage_threshold(fidelity: str) -> float:
    # "Large main colours" are deliberately based on total visible mass, not
    # only chromatic mass.  This prevents a tiny saturated accent from stealing
    # a protected slot in an otherwise neutral image.
    return {
        "Fast": .085,
        "Balanced": .055,
        "Faithful": .035,
        "Exact": .025,
    }.get(str(fidelity or "Faithful"),.035)


def summarize_hue_families(colors: Sequence[Sequence[int]], weights: Sequence[float], *,
                           fidelity: str="Faithful", max_families: int | None=None,
                           chroma_threshold: float=4.5) -> list[HueFamilySummary]:
    """Summarise dominant chromatic families by weighted visible coverage.

    A family receives at most one representative: the colour with the strongest
    combination of area and chroma.  Families below the fidelity-dependent
    coverage floor are treated as texture/accent colours rather than guaranteed
    palette anchors.
    """
    total=sum(max(0.0,float(weights[i])) for i in range(min(len(colors),len(weights)))) or 1.0
    buckets: dict[str,dict] = {}
    for i,(rgb,w) in enumerate(zip(colors,weights)):
        weight=max(0.0,float(w))
        if weight<=0: continue
        family=dominant_hue_family(rgb,chroma_threshold=chroma_threshold)
        if family is None: continue
        _L,C,_H=oklab_metrics(_rgb(rgb))
        row=buckets.setdefault(family,{'weight':0.0,'members':[]})
        row['weight']+=weight
        row['members'].append((i,weight,C,_rgb(rgb)))
    threshold=_coverage_threshold(fidelity)
    summaries=[]
    for family,row in buckets.items():
        coverage=float(row['weight'])/total
        if coverage+1e-12 < threshold:
            continue
        # Area dominates. Chroma only breaks close calls so a vivid family
        # representative is preferred over a muddy shade with similar mass.
        i,w,C,rgb=max(row['members'],key=lambda item:(item[1]*(1.0+min(40.0,item[2])/160.0),item[1],item[2],-item[0]))
        summaries.append(HueFamilySummary(family,float(row['weight']),coverage,int(i),rgb,float(C)))
    summaries.sort(key=lambda s:(-s.weight,-s.representative_chroma,s.representative_index,s.family))
    if max_families is not None:
        summaries=summaries[:max(0,int(max_families))]
    return summaries


def dominant_hue_anchors(colors: Sequence[Sequence[int]], weights: Sequence[float], cap: int, *,
                         fidelity: str="Faithful") -> tuple[list[int],dict]:
    """Return palette indices that must be reserved before shade/detail slots."""
    cap=max(0,int(cap))
    summaries=summarize_hue_families(colors,weights,fidelity=fidelity,max_families=cap)
    anchors=[s.representative_index for s in summaries]
    return anchors,{
        'dominant_hue_families':tuple(s.family for s in summaries),
        'dominant_hue_coverage':{s.family:round(s.coverage,5) for s in summaries},
        'dominant_hue_anchor_indexes':tuple(anchors),
        'dominant_hue_preservation':bool(summaries),
    }


def protected_hue_families(colors: Sequence[Sequence[int]], weights: Sequence[float], cap: int, *,
                           fidelity: str="Faithful") -> tuple[str,...]:
    return tuple(s.family for s in summarize_hue_families(colors,weights,fidelity=fidelity,max_families=max(0,int(cap))))
