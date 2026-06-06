# Edu-PPRM Label Taxonomy

First version taxonomy for Phase 2. Keep labels compact; do not add new labels before pilot annotation exposes a repeated need.

## intervention_needed

### true

Definition: Tutor should intervene now because the current trace contains an actionable error or unsafe ambiguity.

Positive examples:
- A local arithmetic error changes the next result.
- The student misreads a given quantity and continues from it.

Negative examples:
- The student is correct so far.
- The student already notices and fixes the issue.

Common confusions:
- Do not mark true only because the solution differs from the reference.
- Do not mark true when evidence is insufficient.

### false

Definition: No intervention is needed at the current point.

Positive examples:
- No-error trace.
- A minor wording issue does not affect the math.
- The student self-corrects before tutor action is useful.

Negative examples:
- A hidden formula misuse affects later steps.
- The student copied a condition incorrectly.

Common confusions:
- False is not the same as unknown.
- False should not be used for unclear work with missing evidence.

### uncertain

Definition: The annotator cannot safely decide whether intervention is needed from the available information.

Positive examples:
- Only a final answer is shown.
- The problem statement is ambiguous or missing.

Negative examples:
- A clearly wrong substitution is visible.
- A fully correct derivation is visible.

Common confusions:
- Use uncertain instead of inventing a hidden mistake.
- Use insufficient_information repair type with uncertain when appropriate.

## minimal_repair_type

### no_intervention_needed

Definition: No repair should be given because no tutor intervention is needed.

Positive examples:
- Correct trace.
- Self-corrected earlier slip.

Negative examples:
- Incorrect formula use.
- Missing condition check.

Common confusions:
- Do not use this for insufficient information.

### ask_to_recompute_local_expression

Definition: Ask the student to recompute a specific arithmetic or algebraic expression.

Positive examples:
- 7*8 written as 54.
- 2a+3=-3 solved as a=-2.

Negative examples:
- Wrong formula selected.
- Problem quantity misunderstood.

Common confusions:
- Do not reveal the corrected value unless hint policy allows it.

### ask_to_reinterpret_given_quantity

Definition: Ask the student to revisit the meaning of a number, unit, condition, or relation in the problem.

Positive examples:
- Treats three times as many tires as three times as many bicycles.
- Confuses total distance with one leg.

Negative examples:
- Correct interpretation but arithmetic slip.
- Formatting-only issue.

Common confusions:
- Use this before formula repair when the formula is wrong because the quantity was misread.

### ask_to_rewrite_equation_or_expression

Definition: Ask the student to set up or rewrite the equation/expression that represents the problem.

Positive examples:
- Uses x+5=20 instead of 5x=20.
- Drops parentheses when translating a word problem.

Negative examples:
- Equation is right but solved incorrectly.
- Unit conversion mistake.

Common confusions:
- Separate representation errors from downstream computation errors.

### ask_to_check_operation_or_formula

Definition: Ask the student to verify the chosen operation, identity, theorem, or formula.

Positive examples:
- Uses area formula for perimeter.
- Uses simple interest formula for compound interest.

Negative examples:
- Correct formula with wrong substitution.
- Correct operation but arithmetic slip.

Common confusions:
- Do not overuse when the issue is only a local expression.

### ask_to_check_unit_conversion

Definition: Ask the student to check conversion between units or scales.

Positive examples:
- Minutes converted to seconds incorrectly.
- Centimeters treated as meters.

Negative examples:
- No unit change is involved.
- Formula choice is the real issue.

Common confusions:
- Use local recomputation if the conversion setup is right but arithmetic is wrong.

### ask_to_justify_inference

Definition: Ask the student to justify a logical inference or skipped reasoning step.

Positive examples:
- Claims two expressions are equal without a condition.
- Infers monotonicity without support.

Negative examples:
- Pure arithmetic slip.
- Question asks only for final numeric computation.

Common confusions:
- Jumping steps can be acceptable when mathematically standard.

### ask_to_compare_with_problem_condition

Definition: Ask the student to compare a step or answer against an explicit problem condition.

Positive examples:
- Answer violates positivity.
- Chosen value fails a boundary condition.

Negative examples:
- No explicit condition applies.
- Local computation has not reached a checkable condition.

Common confusions:
- Use substitute_back when checking an equation rather than a story condition.

### ask_to_substitute_back

Definition: Ask the student to substitute the result back into the equation or original requirement.

Positive examples:
- Extraneous root from squaring.
- Solved variable should be checked in both equations.

Negative examples:
- Initial setup is plainly wrong.
- No candidate value exists yet.

Common confusions:
- This is a verification repair, not a formula-selection repair.

### ask_clarifying_question

Definition: Ask a clarification question because the student's notation, statement, or problem context is ambiguous.

Positive examples:
- Student uses x without defining it.
- Problem wording allows two interpretations.

Negative examples:
- The mistake is clear enough to repair directly.
- The trace is simply missing all work.

Common confusions:
- Do not use this to avoid deciding a clear error category.

### insufficient_information

Definition: There is not enough information to choose a safe minimal repair.

Positive examples:
- Only final answer shown.
- Problem text missing and no recoverable question field.

Negative examples:
- Trace clearly shows a local arithmetic error.
- Student has a correct complete solution.

Common confusions:
- Pair with intervention_needed uncertain, not false, unless no intervention is clearly appropriate.

## hint_level

### none

Definition: No hint is needed.

Positive examples:
- No-error trace.
- Self-corrected trace.

Negative examples:
- Student needs a prompt to revisit a step.

Common confusions:
- Do not use none with a nontrivial repair request.

### low

Definition: Point to the local step or condition without naming the error.

Positive examples:
- Ask the student to look again at step 2.
- Ask which quantity the 3 multiplies.

Negative examples:
- Show a worked example.
- Name the exact formula error.

Common confusions:
- Low hints should preserve student discovery.

### medium

Definition: Name the type of issue or ask a targeted repair question without solving it.

Positive examples:
- Ask whether the operation should be multiplication or addition.
- Ask to check unit conversion.

Negative examples:
- Give the next computed value.
- Give the final answer.

Common confusions:
- Medium can name error type but should not complete the step.

### high

Definition: Provide a strong scaffold or micro-example while still avoiding the full solution.

Positive examples:
- Show a parallel tiny example.
- State the relevant formula but ask the student to substitute.

Negative examples:
- Solve the student's actual next step.
- Reveal final answer.

Common confusions:
- High is still not a full solution.

### forbidden_full_solution

Definition: A proposed hint would reveal too much and should not be used.

Positive examples:
- The only hint would be the final answer.
- The next step is exactly the target answer.

Negative examples:
- A local non-revealing prompt exists.
- A micro-example can avoid leakage.

Common confusions:
- This labels hint safety, not whether the student is wrong.

## leakage_constraint

### do_not_reveal_final_answer

Definition: Feedback must not reveal the final answer.

Positive examples:
- Word problem asks for one number and next step computes it.
- Multiple choice answer can be inferred from hint.

Negative examples:
- The final answer is already provided by the student and the task is to check reasoning.

Common confusions:
- This can coexist with a local hint.

### do_not_solve_next_step

Definition: Feedback must not perform the student's next required step.

Positive examples:
- Ask them to recompute 48/2, do not state 24.
- Ask them to set up the equation, do not write it for them.

Negative examples:
- A conceptual definition can be provided without solving.

Common confusions:
- Do not confuse with final-answer leakage; both may apply conceptually, but choose the stricter local constraint.

### can_point_to_local_step_only

Definition: Feedback may identify the relevant step but not explain the full correction.

Positive examples:
- Step 3 is where the units change.
- Check the equation in line 2.

Negative examples:
- Explaining the formula and substitution is necessary.
- No step exists to point to.

Common confusions:
- Use with low hint level.

### can_name_error_type

Definition: Feedback may name the error category while avoiding the correction.

Positive examples:
- This looks like a unit conversion issue.
- Check the operation used here.

Negative examples:
- Naming the category gives away the answer in a fragile puzzle.

Common confusions:
- Usually pairs with medium hint level.

### can_show_micro_example

Definition: Feedback may use a small analogous example that does not solve the target problem.

Positive examples:
- Use a 2-minute to seconds conversion example.
- Show a simpler substitution check.

Negative examples:
- The micro-example uses the same numbers as the target.
- The example reveals the final answer pattern too directly.

Common confusions:
- Usually pairs with high hint level.
