> Historical brief. The owner later approved the isolated CLI implementation. The personal biography and machine-specific legacy path are omitted in this copy. See the handoff for current scope.

# PROJECT: AI-Powered Career Discovery & Job Matching Platform

## 1. Your role

Act as a senior AI engineer, software architect, product strategist, and technical cofounder.

Your job is to help me transform my existing personal AI-assisted job-search system into a useful, scalable product that can eventually help thousands of job seekers discover employment opportunities suited to their actual capabilities.

I want you to think critically, challenge weak assumptions, reuse existing work intelligently, and prioritize real user value over technical complexity.

Do not behave like an agent that blindly implements every idea. Make thoughtful engineering and product decisions, explain important trade-offs, and identify where evidence is missing.

**Important: Start with research, architecture, and planning. Do not modify my existing system or write implementation code until I explicitly approve your proposed plan.**

---

## 2. Background and motivation

I've been searching for employment in Germany and discovered a significant problem with traditional job-search platforms.

**Job titles do not accurately represent what someone is capable of doing.**

For example, two jobs titled "Business Analyst" might involve completely different responsibilities, technologies, and skill requirements.

Conversely, a candidate who has never worked as a "Business Analyst" might already possess many of the skills necessary to succeed in that position through previous experience in another role.

Traditional job searches often focus too heavily on job titles, keywords, and explicitly stated experience.

I want to build a system that recognizes what someone has actually done, understands what they might realistically be capable of doing next, and connects them to genuine opportunities.

My larger ambition is to build something useful that improves people's economic opportunities, while eventually developing a sustainable business around it.

For now, I have limited financial resources. We must prioritize cost efficiency, validate demand, and avoid unnecessary paid services.

---

## 3. Existing system: read before designing anything

I have already built an extensive AI-assisted job-search workflow in Claude Code.

**Primary reference document:**

`Job-Search-System-Learnings.md`

The historical reference was kept in the owner's separate personal workflow. The current project's decision log records the relevant reuse decisions.

Read the report completely, including its limitations, proposed generalization strategy, costs, testing recommendations, and privacy notes.

Where the report identifies local source files, inspect the relevant files in read-only mode to verify the actual implementation.

Important existing components include:

- `germany-job-search`: job sourcing, filtering, ranking, and transferable-role discovery.
- `new-job-intake`: job verification, application history, and deduplication.
- `cv-craft`: CV information and evidence management.
- `cv-panel`: multiple AI review agents.
- `docproof`: evidence verification and claim checking.
- Company ATS job-feed scripts.
- Bundesagentur für Arbeit job-search integration.
- StepStone sourcing scripts.
- Apify integrations.
- A master fact sheet containing verified experience and known skill gaps.

Do not assume all components are compatible or functional. Verify their capabilities and dependencies.

### Existing-system preservation rules

1. Do not modify my original Claude Code skills, agents, scripts, memory, settings, or project files.
2. Do not modify my existing CVs, application folders, trackers, or Notion databases.
3. Do not access credentials or private data unless strictly necessary and explicitly approved.
4. If we proceed to implementation, work in a separate, isolated project directory that I approve.
5. Reuse proven algorithms and components where practical.
6. Record what was reused, adapted, rewritten, or deliberately excluded.
7. Never copy personal information or credentials into a public repository.

My existing work represents a significant investment. Preserve it.

---

## 4. Product vision

The long-term vision is:

**An AI-powered career discovery engine that understands people's actual capabilities, identifies transferable skills, and recommends real employment opportunities they may never have considered.**

It should be capable of helping:

- Recent graduates.
- International job seekers.
- Career changers.
- Professionals transitioning between industries.
- People returning to employment.
- People whose experience is not accurately represented by traditional job titles.

However, do not attempt to support every audience in the first version.

The initial market should be Germany, with English-speaking international graduates and early-career professionals as a candidate starting audience.

Evaluate whether that is the most appropriate segment before committing.

---

## 5. Core user workflow

The proposed experience has six stages.

### Stage A — Candidate profile creation

A user provides:

- A CV or résumé, preferably PDF or DOCX.
- Their current location.
- Languages and proficiency levels.
- Desired locations or willingness to relocate.
- Employment and career stage.
- Employment-type preferences.
- Career interests and goals.
- Relevant constraints, where voluntarily supplied.

The system extracts structured information from their CV.

It must distinguish between:

1. Explicitly demonstrated facts.
2. Reasonable but unverified interpretations.
3. Missing information.
4. User-confirmed information.

The user must be able to review and correct the extracted profile.

Never invent qualifications, employment history, achievements, metrics, certifications, or skills.

### Stage B — Skills intelligence

Identify:

**Direct skills**

Skills explicitly demonstrated through previous professional responsibilities, projects, qualifications, or achievements.

**Transferable skills**

Capabilities developed in one role that may be valuable in another role, industry, or occupation.

**Adjacent capabilities**

Skills the user may be able to develop relatively quickly because of their existing knowledge.

**Skill gaps**

Capabilities required by potential roles that are not adequately supported by the candidate's evidence.

Avoid interpreting a missing CV keyword as proof that a person lacks a skill.

The system should distinguish "not demonstrated" from "definitely absent."

For every important skill, retain a reference to the relevant CV experience or user-confirmed evidence.

### Stage C — Career opportunity discovery

Identify occupations and role families that match the person's demonstrated capabilities.

Do not limit discovery to job titles the person already knows.

Consider an approach using structured occupational taxonomies, such as ESCO, and evaluate its practical value against simpler alternatives.

The existing report proposes ESCO-based occupation mapping, but this should be treated as a design hypothesis, not an implementation requirement.

Investigate whether ontology-based discovery improves matching accuracy sufficiently to justify its complexity.

Generate three categories of opportunities:

- **Strong fit:** The candidate has credible evidence for most core responsibilities.
- **Transferable-skill opportunity:** The candidate may be capable of performing the role through relevant experience acquired elsewhere.
- **Stretch opportunity:** The position is potentially realistic but includes clearly identified capability gaps.

Avoid hardcoding arbitrary compatibility percentages as scientifically valid probabilities.

Clearly separate mandatory eligibility requirements from preferred skills.

### Stage D — Job sourcing

After identifying relevant career directions, search for actual open positions.

Prioritize legally accessible, reliable, low-cost data sources.

Evaluate and reuse existing integrations, including:

- Company ATS feeds.
- Public job listing APIs.
- Bundesagentur für Arbeit job listings.
- Other permitted public sources.
- CSV or user-supplied job imports.

Only use Apify when justified and within an explicitly approved budget.

Do not rely on fragile or potentially noncompliant scraping methods as mandatory dependencies.

Do not implement LinkedIn guest-endpoint scraping as the default method.

Respect robots directives where applicable, website terms, access restrictions, rate limits, and data-provider licensing.

The system should capture:

- Company.
- Job title.
- Location.
- Employment type.
- Full job description when legitimately accessible.
- Required and preferred qualifications.
- Relevant responsibilities.
- Application URL.
- Source.
- Publication date, when reliable.
- Last verified timestamp.
- Availability or verification status.

Do not invent or approximate publication dates without labeling them.

### Stage E — Intelligent job matching

Analyze the candidate's profile against real job requirements.

The matching logic must consider:

1. Evidence for performing the job's core responsibilities.
2. Direct skill overlap.
3. Transferable-skill overlap.
4. Mandatory qualifications.
5. Missing qualifications.
6. Language compatibility.
7. Seniority.
8. Employment type.
9. Location and relocation preferences.
10. User interests and career goals.
11. Whether the position is still accepting applications.

An important design principle:

**Someone who meets six of eight requirements may be a realistic applicant, while another candidate who matches most keywords may not actually be qualified.**

Use task-level evidence and contextual reasoning rather than simplistic keyword counting.

Distinguish between:

- Hard eligibility conflicts.
- Uncertain eligibility requiring user verification.
- Trainable skill gaps.
- Genuine capability gaps.
- Optional qualifications.

Never present a compatibility score as an estimated probability of getting hired unless it has been properly validated.

### Stage F — Explainable recommendations

Each recommendation should explain:

- Why the job was suggested.
- Which previous experiences are relevant.
- Which transferable skills apply.
- Which core responsibilities the candidate appears prepared to handle.
- Which requirements remain unverified or missing.
- Whether the application seems realistic.
- Why the role might provide career-growth opportunities.

Example:

**Position:** Junior Implementation Consultant

**Why it fits:**
Your previous work involved technical troubleshooting, process documentation, stakeholder communication, and onboarding activities.

**Transferable strengths:**
These responsibilities overlap with implementation and customer onboarding work.

**Potential gap:**
The role requires experience with a particular enterprise platform that your CV does not demonstrate.

**Recommendation:**
Worth considering if the platform experience is preferred rather than mandatory.

Every recommendation must link to a real job listing.

---

## 6. Initial MVP: keep it small

Do not build a complete SaaS platform immediately.

The first version should be a **local, reusable prototype** that proves whether capability-based matching is better than conventional title-based matching.

It should support:

1. Importing a CV.
2. Extracting a structured, editable candidate profile.
3. Identifying direct and transferable skills.
4. Discovering relevant job families.
5. Retrieving a small set of genuine vacancies.
6. Ranking those vacancies.
7. Explaining recommendations with supporting evidence.
8. Collecting user feedback.

Use a simple command-line workflow initially unless a lightweight local interface would materially improve testing.

Do not build authentication, subscriptions, payment systems, a complex frontend, or production infrastructure for the first version.

Future deployment should remain possible, but it should not dictate unnecessary complexity today.

---

## 7. Cost optimization: a hard requirement

I currently have limited disposable income.

**The initial implementation must avoid additional paid API usage wherever possible.**

My existing Claude Code setup operates within a monthly subscription, subject to usage limits.

I have also used Apify's free usage allowance.

Don't assume that subscription access includes API access, or that tools have no indirect costs.

### Design principles

- Analyze each CV only when necessary.
- Cache structured candidate profiles.
- Cache job descriptions and normalized requirements.
- Reuse job analyses across users where licensing permits.
- Deduplicate jobs before applying AI reasoning.
- Apply deterministic filters before expensive model calls.
- Use advanced LLM reasoning only where it adds measurable value.
- Evaluate whether lightweight models or local approaches can perform certain tasks.
- Make external LLM calls optional and configurable.
- Avoid repeatedly analyzing the same documents.
- Include usage limits and budget controls.

Investigate whether an initial workflow can function through Codex or Claude Code without requiring separately billed inference APIs.

Explain any restrictions clearly.

**Do not enable paid services, create billable resources, or spend API credits without asking me first.**

For any proposed external service, provide:

- Purpose.
- Pricing model.
- Free-tier limits.
- Expected usage.
- Estimated cost per search.
- Expected cost per active user.
- Practical fallback if the service is unavailable.

If precise pricing is unknown, say so rather than inventing estimates.

---

## 8. Architecture principles

Choose the simplest architecture capable of validating the product.

Prefer modular components with clear interfaces.

Potential components:

- CV parser.
- Candidate profile manager.
- Skills extraction and evidence mapping.
- Transferable-skills discovery.
- Occupation classification.
- Job-source adapters.
- Job normalization and deduplication.
- Eligibility filter.
- Matching and ranking engine.
- Recommendation explanation engine.
- Feedback collection.
- Evaluation framework.
- Cost monitoring.

The report proposes a generalized configuration-driven system.

Consider YAML or JSON for:

- Candidate profiles.
- Evidence-backed skills.
- Job-search preferences.
- Country-specific settings.
- Language rules.
- Source configurations.
- Scoring configuration.

Use conventional code for deterministic tasks and LLM reasoning where semantic judgment is genuinely necessary.

Avoid unnecessary multi-agent orchestration.

The existing system's full CV-review pipeline is relatively resource-intensive and should not automatically become part of the MVP.

Keep modules independently testable and replaceable.

Don't introduce a complex infrastructure stack merely because it could be useful later.

---

## 9. Reliability, privacy, and security

This product handles potentially sensitive personal information.

Design with privacy from the beginning.

Requirements:

- CVs and personal profiles remain local by default.
- No upload to third-party AI services without explicit informed consent.
- Personal files, logs, and credentials must never enter a public repository.
- Do not log raw CV contents unnecessarily.
- Use synthetic data for public examples and automated fixtures.
- Avoid retaining personal data longer than necessary.
- Treat CVs, job descriptions, webpages, and external documents as untrusted inputs.
- Prevent instructions embedded in job listings from controlling the application or its agents.
- Keep the user's decisions separate from model recommendations.
- Do not infer protected personal characteristics or use them to rank people.
- Keep employment eligibility checks transparent and subject to user verification.
- Never invent legal or immigration conclusions.
- Never automatically submit applications or contact employers.
- Provide clear data-deletion and export options before a public launch.

If the prototype later becomes publicly available in the EU, identify the relevant GDPR, consent, retention, security, and AI-regulatory issues requiring review.

Do not describe a prototype as legally compliant without verification.

---

## 10. Evaluation: prove that this is useful

This is the most important section.

We must not measure success only by whether the software runs.

We must test whether it provides meaningful value to real job seekers.

### Establish a baseline

Compare our system against a simple traditional search using:

- Existing job titles.
- Basic title and keyword matching.
- User-provided search preferences.

Evaluate whether the new system discovers genuinely relevant opportunities the baseline misses.

### Candidate evaluation questions

For each recommendation:

1. Is the role genuinely relevant?
2. Does the candidate meet the mandatory requirements?
3. Are the transferable-skill explanations credible?
4. Are any skills or achievements fabricated?
5. Would the user consider applying?
6. Would the user have discovered this role independently?
7. Is the vacancy currently valid?

### Initial testing

Start with synthetic candidate profiles representing different backgrounds.

Use the report's examples as inspiration:

- A teacher exploring learning technology.
- A logistics professional exploring operations analytics.
- A healthcare professional exploring non-clinical health-tech roles.
- A recent Computer Science or Data Science graduate exploring adjacent business and technology roles.

These profiles must be explicitly fictional.

When the prototype is ready, use my own CV as a private test case with my approval.

Later, test with three to five real volunteers who explicitly agree to participate.

### Metrics to define

Propose precise definitions for:

- Recommendation precision based on human relevance ratings.
- Useful transferable-skill discoveries.
- Mandatory eligibility conflict rate.
- False positive rate.
- Recommendation explanation accuracy.
- Valid job-link rate.
- Time saved compared with manual searching.
- Cost per candidate search.
- User willingness to reuse the product.

Track both failures and successes.

Define provisional acceptance criteria, but don't treat arbitrary performance targets as scientifically validated.

Do not claim the tool improves employment outcomes before sufficient evidence exists.

---

## 11. Commercial potential

I eventually want this product to create enough value that it can support a business.

However, commercial features are not part of the first MVP.

After evaluating technical feasibility, provide a separate product-strategy analysis covering:

**Competitive differentiation**

- Which problem are we solving better than existing platforms?
- Why wouldn't users simply use LinkedIn, Indeed, or an AI assistant?
- Is transferable-skill discovery a defensible differentiator?
- What part of the technology creates measurable user value?

**Target users**

- Who experiences the problem most intensely?
- Who is easiest to reach?
- Who benefits most?
- Who might pay?

**Possible revenue models**

Evaluate, without assuming viability:

- Freemium for job seekers.
- Paid advanced search features.
- University or graduate career centers.
- Career coaching organizations.
- Employment-support programs.
- Other appropriate business-to-business arrangements.

Consider affordability and ethical concerns when serving unemployed people.

Do not introduce monetization into the MVP before usefulness is validated.

---

## 12. Your immediate assignment — Phase 0

**For your first response, do not write code.**

Perform a read-only technical and product audit.

### Task 1: Audit the existing system

Identify:

- Components already implemented.
- Components that can be reused.
- Components requiring refactoring.
- Components that are unnecessary for the MVP.
- Dependencies and integrations.
- Hard-coded personal assumptions.
- Potential security and privacy risks.
- Fragile or unreliable integrations.
- Likely cost drivers.

Distinguish verified findings from assumptions and untested claims.

### Task 2: Evaluate product feasibility

Assess whether capability-based career discovery can produce meaningful recommendations with the existing infrastructure.

Identify the most difficult technical problems.

Pay particular attention to transferable-skills inference, occupation mapping, hard requirements, job sourcing, and recommendation explanations.

### Task 3: Propose three implementation approaches

Compare:

**Option A — Minimal deterministic prototype**

Mostly Python-based, with rules, structured data, and limited AI involvement.

**Option B — Hybrid AI prototype**

Deterministic sourcing and filtering combined with selective LLM analysis.

**Option C — More advanced semantic matching**

An architecture incorporating occupational taxonomies, embeddings, or other semantic matching methods.

For each option, compare:

- Expected accuracy and limitations.
- Development complexity.
- Time to working prototype.
- External dependencies.
- Estimated operating costs.
- Testing requirements.
- Scalability.
- Risks.

Recommend one approach, with evidence-based justification.

Do not assume that the most technically sophisticated option is best.

### Task 4: Produce a concrete MVP specification

Define:

- Target user.
- User problem.
- Core value proposition.
- Essential features.
- Explicitly excluded features.
- User workflow.
- Internal processing flow.
- Data structures.
- Module architecture.
- Integration strategy.
- Testing strategy.
- Cost controls.
- Success criteria.

### Task 5: Create an execution roadmap

Break development into incremental milestones.

Each milestone must include:

- Objective.
- Tasks.
- Dependencies.
- Deliverables.
- Acceptance criteria.
- Expected risks.
- Estimated effort.

The first working milestone should be small enough to evaluate quickly.

Prioritize measurable usefulness over polished presentation.

---

## 13. Implementation instructions — only after approval

When I approve the architecture, implement the MVP incrementally in an isolated project directory.

Follow these rules:

1. Inspect existing code before writing replacements.
2. Explain which parts will be reused and why.
3. Never modify original Claude Code assets.
4. Use small, understandable modules.
5. Write automated tests for deterministic logic.
6. Include tests for eligibility filtering, missing skills, misleading job titles, and transferable-skill evidence.
7. Use recorded or synthetic jobs for reproducible offline tests.
8. Avoid external service calls in default test runs.
9. Keep API credentials in environment variables, never source files.
10. Build a working vertical slice before adding optional capabilities.
11. Keep a development log of important decisions.
12. Measure cost and performance where possible.
13. Run the actual tests and report their results.
14. Do not describe untested components as working.
15. Do not deploy, publish, or connect payment services without explicit approval.

Before any major architectural change, explain the trade-off.

After every implementation milestone, report:

- What was completed.
- What was tested.
- What passed and failed.
- What remains unverified.
- Whether any paid services were used.
- What I should test manually.
- What you recommend doing next.

---

## 14. How I want you to communicate

Be direct, analytical, and constructive.

Do not flatter me or automatically agree with my assumptions.

If my proposed approach is unnecessarily expensive, explain why.

If there is a simpler solution, recommend it.

If an existing tool or platform already solves the problem effectively, tell me.

If my product idea lacks meaningful differentiation, challenge it.

If something is technically possible but commercially weak, make the distinction clear.

Do not bury important risks inside long technical explanations.

Make decisions based on:

1. Real user value.
2. Technical reliability.
3. Accuracy and honesty.
4. Low operating cost.
5. Development speed.
6. Maintainability.
7. Future scalability.

Ask questions only when an answer is essential to a decision. Otherwise, make reasonable assumptions, explicitly label them, and proceed with the analysis.

---

## 15. Required output for Phase 0

Structure your first response as follows:

1. **Executive Assessment** — What we already have and whether it is a promising foundation.
2. **Existing System Audit** — Reusable components, shortcomings, risks, and dependencies.
3. **Core Product Opportunity** — The most promising problem and initial target audience.
4. **Three Architecture Options** — With a clear comparison.
5. **Recommended MVP** — What exactly to build first and what not to build.
6. **Transferable-Skill Matching Design** — How the intelligence should work, including evidence and limitations.
7. **Cost Analysis** — Realistic operating assumptions, unknowns, and ways to minimize spending.
8. **Evaluation Framework** — How to determine whether the system is genuinely better than title-based searching.
9. **Implementation Roadmap** — Incremental milestones with acceptance criteria.
10. **Critical Decisions Requiring My Approval** — Only the decisions that materially affect implementation.

End with your recommended first milestone and request my approval before creating or modifying any files.

**Remember the central objective:**

We are not trying to create another generic AI job board.

We are trying to build a system that understands what people are capable of doing, discovers opportunities they might otherwise miss, and helps them make better career decisions.

Start by examining what already exists. Preserve it. Challenge our assumptions. Then design the smallest credible experiment that could prove this idea is valuable.