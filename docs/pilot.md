# Pilot protocol

## Vacancy supply

Use the fictional technical graduate scenario. On the first day, refresh the reviewed local board list and save a coverage snapshot. Repeat about seven days later without changing the corpus policy or candidate constraints. Capture employer counts, relevant role-family counts, repeats and new jobs. Inspect the listed candidates against the employer’s wording. Record open status, role scope, employment, working language, location and unresolved mandatory conditions. The provisional gate is at least ten plausible in-scope openings spread over three employers and two role families in each snapshot. Store only allowed vacancy text and aggregate findings locally.

## Comparison

Use a fixed corpus and clock for baseline, task and any hybrid run. Use the same preferences, actionable and verify-first definitions, and a cap of five results per list. Export search --mode both --json to a private file if needed. Assign blind vacancy IDs, shuffle a pooled list containing the union of recommendations and a small low-ranked sample, and save the ordering privately for scoring. Label the jobs before revealing which method selected them. In a second pass, audit the explanation against the candidate’s reviewed evidence and the employer’s description. Use a second reviewer where available and retain honest disagreements.

Ask the candidate which titles and vacancies they already knew before showing the lists. For time comparisons, use a manual or competitor session with the same brief and cap the session at 20 minutes. Rotate which method comes first and record time spent reviewing the profile separately. The primary time outcome is active minutes to find three jobs the participant would consider. Record null when fewer than three were found. Ask if they would use the tool again and record observed reuse separately.

Begin with fictional material. A private test with the project owner and a pilot with three to five volunteers use separate consent, clear deletion arrangements and candidate-side review. Avoid putting participant names, CV excerpts or contact information in the evaluation file.

## Rating

- Relevant means the work and career direction suit the participant.
- Realistic means the responsibilities and stated requirements make the vacancy plausible after review. Use null when the available evidence leaves the judgement unresolved.
- Hard conflict means an explicit mandatory condition conflicts with confirmed information. Record false for a reviewed absence of conflict and null if unresolved.
- Open means the official application path was checked at review time.
- Adjacent means the role is outside the initial title families. Previously known and would consider are answers from the candidate.
- For each method, audit atomic explanation claims for source, scope and the transfer itself. Record unsupported and fabricated claims as failures.

Fill the anonymous example schema in [pilot-input.example.json](pilot-input.example.json), then run:

    python3 -B -m career_discovery evaluate "/path/to/anonymous-pilot.json"

The evaluator reports label coverage for relevance, explicit conflicts and links in each lane. Rates use labelled entries for that outcome. Missing ratings stay null, and a lane without applicable labels has undefined rates. The false-positive denominator uses the labelled negatives in the judgement pool. For a fully relevance-labelled corpus, the evaluator also reports relevant coverage and which jobs neither lane surfaced in the displayed lists. Explanation, time and reuse measures require their own observations. Time savings use paired completed sessions.

## Decision

Require zero fabricated facts and zero confirmed hard conflicts in actionable recommendations. Aim for 19 of 20 valid actionable links, one additional useful discovery for a majority of participants, and precision at least equal to the title baseline. Treat these as project thresholds for a directional pilot. Log negative results and failure examples even if the measured thresholds are reached.

## Prepare the blind review deck

With the selected vacancy corpus in local storage and a confirmed profile, run:

    python3 -B -m career_discovery pilot-pack --profile my-profile --participant p01 --output-dir .state/p01-review

The review deck lists vacancy links in a stable shuffled order and contains no CV text or method labels. It pools up to five actionable and five verify-first results from each method, plus a sample of other jobs. Use `--full-corpus` for a frozen set of up to 100 jobs when collecting relevance labels for every vacancy. The scoring key records each selection's method and lane. Keep it private until the reviewer finishes their first ratings. Copy completed judgements into that key and run evaluate on it. To combine volunteers, collect their anonymous participant entries into one participants array.

For the repeat supply observation, use the same profile revision, task catalogue, employer boards and intake approach. The CLI records the source scope and checks elapsed time before reporting a comparison. Overlapping rejection counts in the coverage report help distinguish source coverage from eligibility and parsing problems.
