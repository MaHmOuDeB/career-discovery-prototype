# B1 held-out fixtures

This set tests task recognition in fictional English and German career evidence and vacancy text. The 30 candidate evidence lines were written and labelled from the public task definitions without consulting matcher vocabulary, implementation, previous fixtures or scores. They describe fictional people and workplaces. A separate blind author is responsible for the companion set of 24 fictional English and German ads in `vacancies.json`, with duty and qualification labels.

Each entry in `evidence.json` has a stable `id`, one past-tense `text` line and an unordered `tasks` array. Label each kind of work the person actually performed. Multiple labels can apply. An empty array means the line supplies no evidence for a catalogue task. Merely observing a meeting, attending a course or distributing someone else’s output does not establish performance of the corresponding task.

Use this set only to score a frozen matcher. Record the matcher version and report results against the original labels. Keep examples, labels and error patterns out of vocabulary development, prompt tuning and threshold selection. If results inform a change, use newly authored held-out material for the next independent evaluation.
