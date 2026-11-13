"""Ticket 08's report: three question types and heading on against off, by separation per Rule."""

from jev_cascade.domain import Clause
from jev_cascade.evaluator import Separation
from jev_cascade.sample_report import StudyInputs, render_study
from jev_cascade.sample_study import Arm, ArmResult, SampleSet


def arm_result(question_type, heading, values):
    return ArmResult(
        arm=Arm(question_type, heading),
        by_rule={
            rule_id: Separation(20, 40, value) for rule_id, value in values.items()
        },
        p_yes={},
    )


def inputs(**overrides):
    clause = Clause("D", 0, 0, 10, "x", "9. Liability", parent_is_heading=True)
    plain = Clause("D", 1, 10, 20, "y")
    args = dict(
        sample=SampleSet(
            by_rule={"R1": (clause, plain), "R2": (plain,)}, near_misses={"R1": 1, "R2": 0}
        ),
        type_results=[
            arm_result("binary", True, {"R1": 0.80, "R2": 0.70}),
            arm_result("score2", True, {"R1": 0.90, "R2": 0.85}),
            arm_result("choice2", True, {"R1": 0.60, "R2": 0.65}),
        ],
        chosen_type="score2",
        heading_off=arm_result("score2", False, {"R1": 0.88, "R2": 0.85}),
        keep_heading=True,
        type_differences={"score2": (0.125, 0.05, 0.2), "choice2": (-0.125, -0.2, -0.05)},
        heading_difference=(-0.01, -0.03, 0.01),
        model_version="jev-1.14.0",
        is_stub=False,
        answers=1357,
    )
    args.update(overrides)
    return StudyInputs(**args)


def test_the_report_compares_the_three_types_per_rule_with_counts_and_states_the_choice():
    markdown = render_study(inputs())

    assert "| R1 |" in markdown and "| R2 |" in markdown
    # Separation beside the held / not-held counts it was computed from.
    assert "0.800 (20/40)" in markdown
    assert "0.900 (20/40)" in markdown
    assert "**Chosen question type: score2**" in markdown
    assert "Mean" in markdown


def test_the_report_compares_heading_on_against_off_and_states_the_choice():
    markdown = render_study(inputs())

    assert "**Heading context: on**" in markdown
    # One Clause of the sample has a heading Parent Line: the only one the heading can change.
    assert "heading-affected" in markdown.lower()
    keep_off = render_study(inputs(keep_heading=False))
    assert "**Heading context: off**" in keep_off


def test_the_report_states_its_rules_before_its_results_and_discloses_the_leak():
    markdown = render_study(inputs())

    assert markdown.index("Decision rules") < markdown.index("Question type")
    assert "selection leak" in markdown
    assert "Binned Share" in markdown  # said not to be read from this sample


def test_a_stub_report_is_labelled_as_carrying_no_signal():
    markdown = render_study(inputs(is_stub=True))
    assert "no signal" in markdown
    assert "no signal" not in render_study(inputs(is_stub=False))


def test_when_every_arm_scores_near_the_ceiling_the_report_says_the_sample_cannot_discriminate():
    high = {"R1": 0.97, "R2": 0.98}
    markdown = render_study(
        inputs(
            type_results=[
                arm_result("binary", True, high),
                arm_result("score2", True, high),
                arm_result("choice2", True, high),
            ],
            heading_off=arm_result("score2", False, high),
        )
    )
    assert "near its ceiling" in markdown
    assert "no difference" in markdown

    # With room to discriminate, the claim is not made.
    assert "near its ceiling" not in render_study(inputs())
