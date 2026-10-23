"""Applicability test on a synthetic detector output with two conditions.

The data are generated here and come from no detector or dataset. In condition
"clear", 2 % of the detections are wrong; in condition "rain", 15 % are wrong and
the indicator values of the wrong detections lie closer to those of the correct
ones. Each frame holds detections of one condition. Frames are divided at random
into a grid part (10 %), a selection part (45 %) and a test part (45 %).

Run: python examples/synthetic_example.py
"""
import numpy as np

import applicability_test as at


def detections(condition, n_frames, share_wrong, wrong_mean, rng):
    frame, u, correct = [], [], []
    for f in range(n_frames):
        k = rng.poisson(6) + 1
        y = (rng.uniform(size=k) >= share_wrong).astype(int)
        frame += [f"{condition}-{f}"] * k
        u += list(np.where(y == 1, rng.beta(2, 20, size=k), rng.beta(2, 2 / wrong_mean - 2, size=k)))
        correct += list(y)
    return {"frame": np.array(frame), "u": np.array(u), "correct": np.array(correct)}


def parts(data, rng):
    frames = np.unique(data["frame"])
    code = dict(zip(frames, rng.choice(["grid", "selection", "test"], size=len(frames), p=[0.1, 0.45, 0.45])))
    which = np.array([code[f] for f in data["frame"]])
    return {p: {k: v[which == p] for k, v in data.items()} for p in ("grid", "selection", "test")}


rng = np.random.default_rng(0)
clear = parts(detections("clear", 6000, 0.02, 0.5, rng), rng)
rain = parts(detections("rain", 6000, 0.15, 0.3, rng), rng)
candidates = at.quantile_candidates(np.concatenate([clear["grid"]["u"], rain["grid"]["u"]]))

print("limit  condition of use  tau      FAP est.  [L, U]              retention  outcome")
for alpha in (0.01, 0.05):
    for name, use in (("clear", clear), ("rain", rain)):
        r = at.applicability_test(clear["selection"], use["test"], candidates, alpha, delta=0.05)
        if r.tau is None:
            print(f"{alpha:<6} {name:<17} -        -         -                   -          {r.outcome}")
            continue
        print(f"{alpha:<6} {name:<17} {r.tau:.4f}   {r.A_hat:.4f}    [{r.L:.4f}, {r.U:.4f}]    {r.retention:.3f}      "
              f"{r.outcome}")
print(f"zero-failure bound at alpha 0.01, delta/2 = 0.025: {at.zero_failure_bound(0.01, 0.025)} units")
