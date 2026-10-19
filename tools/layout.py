"""Folder layout shared by the tools.

ROOT       repository root
ANALYSIS   experiment scripts (they load each other by file name, so they stay in one folder)
RESULTS    recorded results, read-only for every tool
WORK       local folder for the per-detection table cache, exports and reruns (not versioned; WORK_DIR overrides)
RUM        detector outputs and datasets, mounted read-only (RUM overrides; see docs/data.md)
NUSC_META  nuScenes v1.0-trainval metadata folder with scene.json and sample.json (NUSC_META overrides)
"""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
RESULTS = ROOT / "results"
WORK = Path(os.environ.get("WORK_DIR", ROOT / "work"))
RUM = Path(os.environ.get("RUM", "/rum"))
NUSC_META = Path(os.environ.get("NUSC_META", "/nuscenes/v1.0-trainval"))
CACHE = WORK / "cache/tables.pkl"


def load_analysis():
    """Return m6 from analysis/; m1, m2, m3 and m4 are reachable as m6.m1 ... m6.m4."""
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("m6", str(ANALYSIS / "m6_protocol_seeds_weather.py"))
    m6 = importlib.util.module_from_spec(spec)
    sys.modules["m6"] = m6
    spec.loader.exec_module(m6)
    return m6
