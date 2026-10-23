# Guide: how much data to record per condition

Before a recording campaign, the number of independent units each condition needs can be computed from two numbers:
the limit α of the performance target and the error probability δ chosen in the SOTIF analysis. This guide shows the
calculation, what counts as an independent unit, and how the KITTI and nuScenes validation sets compare.

## 1. The zero-failure bound

Units without any false acceptance are the data most favourable to showing that a limit is met. If every per-unit value
is 0 or 1 and the true false acceptance proportion lies just above α, all of n independent units are free of false
acceptances with a probability close to (1 − α)ⁿ. Showing that the limit is met at error probability δ′ therefore
needs at least

```
n ≥ ln δ′ / ln(1 − α)
```

independent units per condition and per part (Eq. 5 of the paper), with δ′ = δ for selecting a threshold and
δ′ = δ/2 for testing it. At δ′ = 0.05 this is about 3/α (the rule of three).

| limit α | units to select a threshold (δ′ = 0.05) | units to test it (δ′ = 0.025) |
|---|---|---|
| 0.1 | 29 | 36 |
| 0.05 | 59 | 72 |
| 10⁻² | 299 | 368 |
| 10⁻³ | 2,995 | 3,688 |
| 10⁻⁴ | 29,956 | 36,887 |

Selecting and testing in one condition therefore needs at least 667 independent units at 10⁻² (299 + 368), with δ = 0.05.

Three properties matter for planning:

- The bound is **necessary, not sufficient**. Every unit with a false acceptance raises the number further, so the
  bound is the minimum for a detector that makes no false acceptance at all in the recorded data.
- It grows **linearly with 1/α** and only **logarithmically with 1/δ′**: a tenfold stricter limit needs ten times the
  units, a tenfold smaller error probability needs fewer than twice as many.
- It does **not apply to the outcome not applicable**, which a few units with many false acceptances can show.

The [units page](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/units.html)
computes the bound for any α and δ, and the
[calculator](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/test.html) gives the
interval and outcome for a given number of units and estimated FAP.

## 2. What counts as an independent unit

The statistical test treats each unit as one independent draw from the distribution of the condition. Consecutive frames
of one recorded sequence share objects, weather, road and sensor position, so they are not independent. Counting them as
independent overstates the evidence, and the stated error probability is then not guaranteed. ISO/PAS 8800 lists nearly
identical consecutive frames, one in the training and the next in the test data, as a lack of independence (Table 11-2).

The unit is therefore the **recorded sequence** (a continuous recording) unless the independence of frames is shown. In
the sequence-level evaluation, each sequence contributes one value, the mean of the per-frame shares over its frames in
the condition. Sequences cut from one continuous log (same vehicle, day and weather) may not be independent either, so
the number of effectively independent units can lie below the number of sequences.

Practical consequences:

1. Plan the number of **sequences**, not frames, per condition.
2. Record each condition in **separate drives**, spread over days, routes and vehicles, so that sequences are not cut from
   one log.
3. Divide whole sequences into the selection part and the test part, never single frames.
4. A rare condition can be recorded more often than it occurs in operation. This changes the FAP over all frames (Eq. 4
   of the paper) but supplies the units that the test per condition requires.

## 3. How public datasets compare

The validation sets used in the case study hold far fewer independent units than the bound requires at the target
limits:

| data | independent units | lowest limit that n units can show to be met |
|---|---|---|
| nuScenes validation set | 150 scenes in total, 67 or 68 per distance condition in a selection or test part, 9 to 12 rain scenes | 150 scenes: 0.020 when selecting (δ′ = 0.05) |
| KITTI validation set | 45 drives in total; 20 in a selection part, 21 in a test part | 20 drives: 0.139 when selecting |
| KITTI as condition of use in the change of dataset | 23 test drives | 0.148 when testing (δ′ = 0.025) |

The last column is 1 − δ′^(1/n), the inverse of the bound. With the recorded sequence as the unit, neither dataset can
show a target limit of 10⁻² to be met in any condition. Counted in frames, every condition reaches the minimum at 10⁻²
and none at 10⁻³, but the frames are not independent (case study results: [`docs/results.md`](../results.md)).

## 4. Checklist before recording

- [ ] Limit α per condition, from the allocation of the acceptance criterion to the detector.
- [ ] Error probability δ, and how many outcomes the safety argument relies on at once (δ is then divided by their
      number, which raises the bound only logarithmically).
- [ ] Conditions, defined by rules that use no detector output (for example a rain label per drive), so that the
      condition of each frame is known before the test.
- [ ] The unit (recorded sequence) and the rule for cutting recordings into sequences.
- [ ] Number of sequences per condition: at least the bound for selecting plus the bound for testing, with a margin for
      sequences that contain false acceptances.
- [ ] A second performance target on missed objects, since a lower threshold exchanges false acceptances for withheld
      correct detections; it needs its own bound at its own limit.
