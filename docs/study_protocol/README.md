# Study protocol

What the case study fixed before any outcome was computed, and how the study departed from it. For readers who check
whether the outcomes were predicted or found afterwards.

| file | content |
|---|---|
| [`predictions_frozen_2026-10-01.md`](predictions_frozen_2026-10-01.md) | the predictions P1 to P5 and the parameters, fixed and recorded with a date in version control on 1 October 2026, before any outcome was computed (paper Sect. 4.4) |
| [`outcomes_and_deviations.md`](outcomes_and_deviations.md) | how each prediction turned out, with its evidence file; the mapping of the frozen classes C0 to C5 to the conditions studied; every deviation from the frozen protocol |

The frozen file is published as frozen, with one phrase changed: on line 5, a reference to a file of the project's
internal decision log reads "recorded in the project's decision log". The frozen file has SHA-256
`f5dde2af3cacc8f862a8fe64f0b7a77e416471cb55409b4777355b8ca60c25ee`. The commit identifiers, the documents `design.md`
and `sample_size.md` and the decision log that it mentions belong to the project's working repository and are not
published; the frozen file also holds one placeholder (`\PH{...}`, P1) that was open when it was frozen.

**Terms of the frozen file.** The frozen file uses the wording of its date. Its "classes" C0 to C5 are mapped to the
conditions studied in [`outcomes_and_deviations.md`](outcomes_and_deviations.md#mapping-of-the-frozen-condition-classes-to-the-conditions-studied);
a target that "applies" or "does not apply" in a class is a performance target that is applicable or not applicable in
a condition of use; a target "established" in a class is a threshold selected in a condition of selection; "frames
resampled" refers to an interval that the study replaced by the Hoeffding-Bentkus bounds. Current terms:
[`../glossary.md`](../glossary.md); the idea of the test: [`../concept.md`](../concept.md).
