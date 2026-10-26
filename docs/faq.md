# Questions and answers

Short answers to the questions a first reader asks most. Each answer links to the page that explains it in full. Terms
are defined in [`glossary.md`](glossary.md).

## What does the test answer?

Whether a performance target that a detector meets with an uncertainty threshold in one condition (the **condition of
selection** c) is also met in another (the **condition of use** c′), when the threshold is used there unchanged. The
target is a limit α on the **false acceptance proportion (FAP)**, the share of wrong detections among the detections the
threshold accepts, averaged over frames. The answer is one of four outcomes: applicable, not applicable, not determined,
or no threshold selected ([`../README.md`](../README.md#what-a-result-means), [`concept.md`](concept.md)).

## What do I need from my detector?

A table with one row per detection: the frame, the condition, an indicator value u (a detection is accepted if
u ≤ τ, the uncertainty threshold), and whether the detection is correct or wrong against the annotations. The recorded sequence (scene, drive) of
each frame is needed for the sequence-level evaluation. Access to the detector itself is not needed
([`../package/README.md`](../package/README.md#input-format),
[`guides/apply-to-your-detector.md`](guides/apply-to-your-detector.md)).

## What is a condition, and what is a potential triggering condition?

A condition is a part of the data defined by a property that can be checked for each detection or frame, for example
the distance of a detection, the weather label of a scene, or the dataset with its detector. A triggering condition is
the ISO 21448 term for a specific condition of a scenario that initiates a system reaction contributing to a hazardous
behaviour. A condition that acts on the input of the detector, such as far distance or rain on the point cloud, but has
not been shown to initiate a hazardous behaviour, is treated as a **potential** triggering condition
([`glossary.md`](glossary.md#safety-terms-iso-21448-sotif)).

## Why not compare the AUROC between the two conditions?

The AUROC measures how well the indicator orders wrong above correct detections. It does not depend on the share of
wrong detections, nor on how they are spread over frames, and it is unchanged when the indicator is rescaled in a way
that keeps the order of its values. The FAP at a fixed threshold depends on all three. In the case study the AUROC of
the existence indicator in rain did not decrease (0.844 clear, 0.856 rain, test part of split 0), and the threshold
transferred from clear weather at the exploratory limit 0.1 was still not applicable in rain on four of five splits
(frame-level evaluation)
([`concept.md`](concept.md#4-four-changes-in-the-detections-and-which-one-auroc-shows)).

## Is "not determined" a pass?

No. It means that the data of the condition of use show neither that the limit is met nor that it is exceeded, because
there are too few independent units or because the FAP lies close to α. The condition of use stays not verified until
more independent units are recorded
([`guides/outcomes-in-a-safety-argument.md`](guides/outcomes-in-a-safety-argument.md)).

## Frames or recorded sequences: what is the independent unit?

The guarantee of the test assumes independent units. Frames of one recorded sequence (consecutive frames of one drive
or scene) share the scene, the weather and the traffic, so they are not independent. Counting frames (frame-level
evaluation) then overstates the evidence; counting whole sequences (sequence-level evaluation) is the safer choice, and
the parts must be formed from whole sequences ([`concept.md`](concept.md#5-the-independent-unit-frame-or-recorded-sequence)).

## How many independent units do I need?

At least n ≥ ln δ′ / ln(1 − α) units without a false acceptance to show a limit α at error probability δ′ (the probability
that the conclusion is wrong): δ′ = δ for
selecting the threshold and δ′ = δ/2 for testing it. At δ = 0.05 and α = 10⁻² these are 299 units for selecting and 368
for testing; at α = 10⁻³, 2,995 for selecting. This can be computed before recording
([`guides/plan-recording.md`](guides/plan-recording.md), the
[units page](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/units.html)).

## Why is the retention reported with every applicable outcome?

A threshold that accepts almost no detection meets any limit on the share of wrong accepted detections. The retention,
the share of correct detections that the threshold accepts, shows what the target costs. In the case study, transferred
thresholds that met 10⁻² in the frame-level evaluation retained at most 29 % of the correct detections
([`../case_study/README.md`](../case_study/README.md#findings)).

## What does the error probability δ cover?

Each applicable or not applicable outcome is wrong with probability at most δ/2 if the units are independent; the
selection uses δ. The bound holds for one outcome at a time. An argument that relies on several outcomes together has
to divide δ by their number ([`../package/README.md`](../package/README.md#assumptions)).

## Does an applicable outcome show that the vehicle is safe in that condition?

No. An outcome concerns the detector as one system element and one performance target. It does not derive α from an
acceptance criterion, does not say how often the condition occurs in operation, and does not cover missed objects,
which need a second target. Tracking, fusion and motion planning lie between the detector and a hazardous behaviour
([`guides/outcomes-in-a-safety-argument.md`](guides/outcomes-in-a-safety-argument.md),
[`concept.md`](concept.md#7-limitations-of-the-study)).

## Do I need KITTI or nuScenes to use the package?

No. The package and the browser pages work on any table of detections. The datasets and the detector outputs are needed
only to rerun the experiments of the case study; the checks of its recorded results need neither
([`../case_study/README.md`](../case_study/README.md#check-and-reproduce)).

## Where are the limitations of the case study?

[`concept.md`, section 7](concept.md#7-limitations-of-the-study): scope, the potential triggering conditions, the rain
label, the definition of a wrong detection, independence and generality (one architecture, one uncertainty method, one
object class).
