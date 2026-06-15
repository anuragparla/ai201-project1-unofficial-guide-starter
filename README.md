# The Unofficial Guide — Project 1

A retrieval-augmented (RAG) assistant that answers questions about **Northeastern
University / Boston student housing**, grounded only in a curated corpus of
official guides, state law, standard leases, transit data, and student forums.

**Pipeline:** Ingestion (`src/ingest/`) → Chunking (`src/chunk/`) → Embedding +
Vector store (`src/retrieval/`) → Retrieval (`src/retrieval/`) → Grounded
generation + Gradio UI (`src/generation/`).

**Run it:**
```bash
pip install -r requirements.txt
python -m src.ingest.ingest      # fetch + clean sources -> documents/clean/
python -m src.chunk.chunk        # chunk -> documents/chunks.jsonl
python -m src.retrieval.embed    # embed -> ChromaDB (chroma_db/)
python -m src.generation.app     # launch the web UI at http://127.0.0.1:7860
```

---

## Domain

This system covers **off-campus and on-campus student housing for Northeastern
University in Boston** — leasing rules, tenant rights, international-student
requirements, on-campus residence-hall policies, and transit access to campus.

This knowledge is valuable because it is **fragmented and hard to synthesize**.
A student trying to navigate the Boston rental market has to cross-reference an
official university portal, a 29-page Massachusetts state-law guide, a binding
standard lease, City of Boston zoning ordinances, and informal crowd-sourced
advice on Reddit — each written for a different audience and none of which
answers a plain-language question like *"how many of us can legally share an
apartment?"* on its own. Official channels are authoritative but siloed and
written in legal/administrative language; the forums are approachable but
unreliable. The RAG bridges that gap: it gives a single, plain-language,
source-attributed answer while preserving the distinction between authoritative
law and anecdotal opinion.

---

## Document Sources

11 sources spanning four structural types (official web pages, long-form
PDFs, crowd-sourced forums, and structured transit data) so the corpus covers
different subtopics *and* different levels of authority.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Northeastern Off-Campus Housing Guidelines | Official web page (HTML) | https://offcampus.housing.northeastern.edu/explore-housing-options/bostonareahousing/ |
| 2 | Northeastern Guide to Residence Hall Living | Official PDF (48 pp) | https://housing.northeastern.edu/wp-content/uploads/2025/08/Guide-to-Residence-Hall-Living-AY25-26-Final.pdf |
| 3 | Office of Global Services (OGS) Housing Guide | Official web page (HTML) | https://international.northeastern.edu/ogs/housing/ |
| 4 | Network Housing Relocation — International Resources | Official web page (HTML) | https://network.housing.northeastern.edu/relocation-resources/resources-for-international-students/ |
| 5 | r/NEU Housing & Roommate Megathread | Forum (Reddit JSON) | https://www.reddit.com/r/NEU/ (housing megathread + comments) |
| 6 | r/boston Housing Wiki | Forum (Reddit wiki JSON) | https://www.reddit.com/r/boston/wiki/housing/ |
| 7 | Massachusetts AG Guide to Landlord and Tenant Rights | State-law PDF (29 pp) | https://www.mass.gov/doc/2025-guide-to-landlord-tenant-rights-11182025/download |
| 8 | Northeastern Leasing Information & Boston Zoning Rules | Official web page (HTML) | https://offcampus.housing.northeastern.edu/get-started/leasing-information/ |
| 9 | Standard Greater Boston Real Estate Board (GBREB) Lease | Standard lease PDF (4 pp) | https://freeforms.com/wp-content/uploads/2021/04/Greater-Boston-Real-Estate-Board-Standard-Form-Apartment-Lease.pdf |
| 10 | MBTA Subway Map and Schedules | Structured transit data (MBTA v3 API) | https://api-v3.mbta.com (routes + stops; normalized to text) |
| 11 | Northeastern International Student Apartment Guide | Official brochure PDF (2 pp, 3-column) | NEU OGS brochure (manually downloaded; https://international.northeastern.edu/ogs/housing/) |

Four of these (sources #5–7, #9) sit behind anti-bot CDNs that reject automated
clients, so the ingester supports a manual-download fallback: the file is fetched
once in a browser, saved to `documents/raw/`, and then flows through the identical
cleaning pipeline.

---

## Chunking Strategy

**Chunk size:** ~240 tokens (≈1,000 characters), measured in the **actual
all-MiniLM-L6-v2 word-pieces** (not characters).

**Overlap:** ~40 tokens (~15%), carried as whole trailing sentences from the
previous chunk.

**Why these choices fit your documents:** The chunk size is dictated by the
embedding model, not the prose. all-MiniLM-L6-v2 silently **truncates input
beyond 256 word-pieces**, so any larger chunk would lose its tail at embedding
time — exactly where a legal clause's exception often lives. Capping the target
at ~240 (leaving room for the model's `[CLS]`/`[SEP]` tokens) guarantees every
chunk embeds in full, which the build verifies (0/267 chunks exceed the limit).
Because the corpus is heterogeneous, the splitter is **structure-aware**: it
breaks on paragraphs first, then sentences, then (only as a last resort) words —
so a short Reddit comment becomes its own chunk instead of being glued to an
unrelated neighbor, while a long legal PDF is split on clause boundaries rather
than mid-sentence. The ~15% overlap matters more at this small size, since legal
rules (a condition in one sentence, its exception in the next) are now more
likely to straddle a boundary; the overlap keeps such pairs co-located in at
least one chunk. **Preprocessing before chunking** was substantial and
per-type: stripping HTML boilerplate (nav/footer/scripts), removing PDF running
headers, page numbers, and dotted-leader tables of contents, collapsing form
fill-in blanks (`Name:_____`), **column-aware extraction** for the 3-column
international brochure, recursively walking Reddit JSON (posts + nested
comments), and normalizing the MBTA's tabular API data into natural-language
sentences. Every chunk also carries metadata (`source`, `url`, `doc_type`,
`source_date`, `chunk_index`) for attribution and authority weighting.

**Final chunk count:** **267 chunks** across the 11 sources (min 50 / avg 216 /
max 253 tokens).

### Sample Chunks

Five representative chunks taken verbatim from `documents/chunks.jsonl`, one from
each of five different source types (law, official web, transit, official
brochure, forum). Each is labeled with its `chunk_id`, source document, and
`doc_type`.

**Chunk 1 — `07_ma_ag_tenant_rights#0028`**
Source: *Massachusetts AG Guide to Landlord and Tenant Rights* (`law`, 221 tokens)
> apartment); and • The actual cost of a new lock and key for the apartment.31
> The landlord should provide a signed receipt for any payment that is made with
> cash or a money order. The receipt must include the amount paid and the date
> the payment was made, and a description of what the payment was for… Landlords
> may not charge tenants or prospective tenants up-front pet fees, broker fees…

**Chunk 2 — `08_neu_leasing_zoning#0000`**
Source: *Northeastern Leasing Information & Boston Zoning Rules* (`official`, 236 tokens)
> A lease is a binding legal contract between you (the tenant or lessee) and the
> landlord (lessor)… A typical lease states the terms of the rental agreement and
> is legally enforceable. Most landlords use the Standard Boston Lease with an
> addendum. 5 Things to Know About Your Lease… Most leases in Boston are 12-month
> leases, starting September 1 and ending August 31…

**Chunk 3 — `10_mbta_subway#0004`**
Source: *MBTA Subway Map and Schedules* (`transit`, 58 tokens)
> The Green Line E serves these stops near Northeastern University: Northeastern
> University, Symphony. The Blue Line stops at the following stations: Bowdoin,
> Government Center, State, Aquarium, Maverick, Airport, Wood Island, Orient
> Heights, Suffolk Downs, Beachmont, Revere Beach, Wonderland.

**Chunk 4 — `11_neu_intl_apartment_guide#0004`**
Source: *Northeastern International Student Apartment Guide* (`official`, 81 tokens)
> Prepare for your apartment search by asking these important questions: • What
> type of apartment am I looking for? How many bedrooms do I need? • Which
> neighborhoods are suitable for me? • Do I need roommates? • Who will be my
> co-signer (see key terms)? • Will I require temporary housing before moving in?
> • Do I have my visa and I-20 to show?

**Chunk 5 — `05_reddit_neu_housing#0000`**
Source: *r/NEU Housing & Roommate Megathread* (`forum`, 236 tokens)
> [MEGATHREAD] Ask your housing related questions here! … Hi, incoming freshman
> here, I have a couple of questions about the Housing Application. When I go to
> the "Housing Online" link on MyNEU and click on "Fall 2021 Housing
> Application" it tells me that the Housing application isn't available even
> though I've already submitted my enrollment deposit over two months ago…

These illustrate the structure-aware splitter at work: the short transit and
brochure chunks (#3, #4) stayed intact as their own units rather than being
glued to neighbors, while the long legal and lease text (#1, #2) was split on
clause/sentence boundaries, and the forum chunk (#5) is clearly marked `forum`
so generation can treat it as anecdotal.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dimensional
vectors), with embeddings L2-normalized and stored in **ChromaDB** using cosine
similarity. Queries are embedded with the same model and the top **k=6** chunks
are retrieved. It was chosen as a strong, fast, free CPU baseline that is a good
fit for a project-scale corpus of mixed legal/official/forum text, and because
its well-known 256-token limit gave a concrete, testable constraint to design
chunking around.

**Production tradeoff reflection:** If deploying for real users with cost no
object, I would weigh four things. **Context length / chunk fit:** MiniLM's
256-token cap forces small chunks; a longer-context embedder (a BGE/E5 variant or
a hosted Voyage/OpenAI embedding) would let me embed whole legal clauses and
lease sections without truncation, improving recall on the long-form sources
(#2, #7, #9). **Domain accuracy:** my corpus mixes statute language with Reddit
slang; a larger, higher-quality model generally ranks nuanced matches better
(e.g. distinguishing a security-deposit *limit* from a deposit *deadline*).
**Multilingual support:** the OGS / international-student audience (#3, #4, #11)
may query in other languages, where a multilingual model (`multilingual-e5`)
would beat English-only MiniLM. **Latency & cost:** MiniLM is free and fast on
CPU; larger local models need a GPU and hosted APIs add per-call latency and
cost. For this project MiniLM's speed and zero cost outweigh the accuracy gains,
so it is the right baseline — but accuracy and multilingual support would be the
first upgrades in production.

---

## Retrieval Test Results

Three queries run live against the populated ChromaDB index via
`python -m src.retrieval.retrieve --k 4 "<query>"`. Scores are cosine similarity
in [0, 1]; the top returned chunks are shown with their source and chunk index.

**Query 1: "What is the maximum security deposit in Massachusetts?"**

| Rank | Score | Source (doc_type) | Chunk |
|------|-------|-------------------|-------|
| 1 | 0.611 | Massachusetts AG Guide to Landlord and Tenant Rights (law) | 28 |
| 2 | 0.474 | Massachusetts AG Guide to Landlord and Tenant Rights (law) | 29 |
| 3 | 0.472 | Massachusetts AG Guide to Landlord and Tenant Rights (law) | 52 |
| 4 | 0.430 | Massachusetts AG Guide to Landlord and Tenant Rights (law) | 44 |

*Why these are relevant:* All four top chunks come from the authoritative MA
state-law guide — the only source that actually governs deposit limits. The
top hit (chunk 28) enumerates exactly what a landlord may collect up front
(first/last month, a deposit of one month's rent, and the cost of a new
lock/key) and chunk 29 covers the separate-escrow-account rule, while chunk 52
is the consumer-protection regulation prohibiting other fees. The query's
domain terms ("security deposit," "Massachusetts") pulled the precise
clause-level chunks rather than generic lease prose, and crucially the
anecdotal forum sources did **not** surface — the desired behavior for a legal
question.

**Query 2: "Which subway line goes to Northeastern campus?"**

| Rank | Score | Source (doc_type) | Chunk |
|------|-------|-------------------|-------|
| 1 | 0.660 | MBTA Subway Map and Schedules (transit) | 0 |
| 2 | 0.640 | MBTA Subway Map and Schedules (transit) | 4 |
| 3 | 0.590 | MBTA Subway Map and Schedules (transit) | 1 |
| 4 | 0.553 | MBTA Subway Map and Schedules (transit) | 3 |

*Why these are relevant:* The top-4 are all from the MBTA transit source, which
is the only document containing line/station data. Chunk 4 explicitly names the
Green Line E stop "Northeastern University" and chunk 1 names the Orange Line's
nearby Ruggles/Massachusetts Avenue stops — together they contain the full
answer. The normalization step that turned the MBTA API's tabular data into
natural-language sentences ("The Green Line E serves these stops near
Northeastern University…") is what let a plain-language query match it so
strongly (0.66 top score).

**Query 3: "Who pays for heat and hot water in a Massachusetts apartment?"**

| Rank | Score | Source (doc_type) | Chunk |
|------|-------|-------------------|-------|
| 1 | 0.635 | Massachusetts AG Guide to Landlord and Tenant Rights (law) | 5 |
| 2 | 0.592 | Massachusetts AG Guide to Landlord and Tenant Rights (law) | 4 |
| 3 | 0.582 | Standard Greater Boston Real Estate Board (GBREB) Lease (official) | 3 |
| 4 | 0.529 | Standard Greater Boston Real Estate Board (GBREB) Lease (official) | 4 |

This query surfaces **both** the law source (rank 1 chunk 5 states "The landlord
must pay for the heat, hot water, and electricity unless a term in the lease…
requires the tenant to pay") and the GBREB lease (rank 3–4), which is exactly the
nuance the question needs — the default rule plus the contractual exception that
can shift it. This mixed-authority retrieval is what enables the
authority-weighting rule at generation time (prefer law over the lease, and say
so).

---

## Grounded Generation

Generation uses the **Groq API** (`llama-3.3-70b-versatile`, `temperature=0`).
Grounding is enforced by **two independent mechanisms**, not by trusting the LLM:

**System prompt grounding instruction:** The model is given absolute, imperative
rules (paraphrased): *"Answer ONLY using facts stated in the CONTEXT passages. Do
not use any prior or outside knowledge. Do not guess or infer beyond the
passages. If the CONTEXT does not contain enough information, reply with EXACTLY
this sentence and nothing else: 'I don't have enough information in my sources to
answer that.' Cite the passage number after each claim, e.g. [1]. If passages
conflict, prefer 'law'/'official' sources over 'forum' (Reddit) sources and say
so."* The context is formatted as numbered, source-labeled passages
(`[1] (source: ...; type: law) <text>`), so the model sees each passage's
authority level. Because temperature is 0 and the refusal string is exact, the
behavior is deterministic and detectable. **Structurally**, retrieval runs
*before* the LLM: if no chunk is available to ground on, the system returns the
refusal **without ever calling the model**, so it has no opportunity to answer
from pretrained knowledge.

**How source attribution is surfaced in the response:** Attribution is built
**programmatically in Python from the retrieved chunks' metadata** — never parsed
from the LLM's prose. After generation, the code reads the `[n]` markers the
model emitted, maps them back to the deduplicated source documents via a mapping
*we* control, and renders a "Sources" list (`source name (doc_type) — url`). The
Gradio UI shows the answer and this source list in two separate boxes. This means
the user always sees the exact documents the answer is grounded in, with their
authority type, and citation numbers in the answer line up with the source list.

### Example Responses

Real output from `src.generation.generate.answer()` (Groq
`llama-3.3-70b-versatile`, `temperature=0`). Source attribution is visible in the
answer text itself (the inline `[n]` markers) and in the appended **Sources**
list.

**Example 1 — in-scope (security deposit)**
> **Q:** What is the maximum security deposit a landlord can charge in
> Massachusetts?
>
> **A:** The maximum security deposit a landlord can charge in Massachusetts is
> equal to one month's rent [1].
>
> **Sources:**
> 1. Massachusetts AG Guide to Landlord and Tenant Rights (law) — https://www.mass.gov/doc/2025-guide-to-landlord-tenant-rights-11182025/download

**Example 2 — in-scope (MBTA access)**
> **Q:** Which MBTA subway line directly connects to Northeastern campus and at
> what station?
>
> **A:** The Green Line E directly connects to Northeastern campus at the
> Northeastern University station [1].
>
> **Sources:**
> 1. MBTA Subway Map and Schedules (transit) — https://api-v3.mbta.com

**Example 3 — out-of-scope (refusal)**
> **Q:** What is the best pizza restaurant in Boston?
>
> **A:** I don't have enough information in my sources to answer that.

The third query is on-topic-sounding (it mentions "Boston") but lies outside the
housing corpus, so the LLM returns the exact refusal string with no Sources
list — grounding working as designed.

---

## Query Interface

The interface is a **Gradio web app** (`python -m src.generation.app`, served at
`http://127.0.0.1:7860`).

**Input field**
- **"Your question"** — a multi-line textbox (2 lines) where the user types a
  natural-language housing question. A placeholder
  (*"e.g. How many unrelated students can share an apartment in Boston?"*) and a
  set of one-click **Examples** prime the user. An **"Ask"** button submits the
  query.

**Output fields**
- **"Answer"** — a textbox (8 lines) showing the grounded answer with inline
  `[n]` citation markers.
- **"Sources"** — a separate textbox (4 lines) listing each cited source as
  `n. source name (doc_type) — url`, built programmatically from the retrieved
  chunks' metadata so citations in the answer line up with this list.

**Sample interaction transcript (one complete query and response):**
```
[Your question]  In Massachusetts, who is responsible for paying for heat and hot water?

                 (user clicks "Ask")

[Answer]   The landlord must pay for the heat, hot water, and electricity unless
           a term in the lease or other written rental agreement requires the
           tenant to pay for these utilities [1]. The Standard GBREB lease can
           shift this responsibility to the tenant [2], but the law source [1]
           takes precedence.

[Sources]  1. Massachusetts AG Guide to Landlord and Tenant Rights (law) —
              https://www.mass.gov/doc/2025-guide-to-landlord-tenant-rights-11182025/download
           2. Standard Greater Boston Real Estate Board (GBREB) Lease (official) —
              https://freeforms.com/wp-content/uploads/2021/04/Greater-Boston-Real-Estate-Board-Standard-Form-Apartment-Lease.pdf
```

---

## Evaluation Report

All five questions were run end-to-end through `src.generation.generate.answer()`.
Responses are summarized; the system also returned a Sources list for each.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What is Boston's "No More Than Four" rule for student renters? | City of Boston zoning bars more than four unrelated undergraduates from sharing a unit. | "The City of Boston does not allow more than four unrelated persons to live together to avoid unsafe overcrowding [1]." → Source #8. | Relevant (#8 at rank 1) | **Accurate** |
| 2 | Max security deposit in MA, and what other up-front payments are allowed? | At most one month's rent; allowed: first month, last month, deposit (≤1 month), new lock/key. | "Max deposit = one month's rent [1]; allowed up-front charges are first full month, last full month, and the cost of a new key and lock; landlords may not charge pet/broker/application fees [1]." → Source #7. | Relevant (#7 dominates top-6) | **Accurate** |
| 3 | As an international student with no U.S. credit, what document helps secure an apartment? | The I-20 form (plus supporting documentation) in place of U.S. credit history. | "Without an I-20 you may be asked for other funding documentation… many landlords require a co-signer… however it is not explicitly stated what specific document you can use [1]." → Source #4. | Relevant (#4 at rank 1) | **Partially accurate** (hedged; see Failure Case) |
| 4 | In a MA rental, who pays for heat, hot water, and electricity? | The landlord, unless the lease shifts it; tenant can't be charged unless separately metered. | "The landlord must pay for heat, hot water, and electricity unless the lease requires the tenant to [1]… a lease (GBREB) may shift it [2], but the law source [1] takes precedence." → Sources #7 (law) + #9. | Relevant (#7 dominates) | **Accurate** |
| 5 | Which MBTA subway line directly connects to NEU's main campus, and what station? | Orange Line via Ruggles; Green Line E also stops at Northeastern station. | "The Green Line E directly connects to campus via the Northeastern University stop [1]; the Orange Line serves nearby stops Ruggles and Massachusetts Avenue [1]." → Source #10. | Relevant (#10 dominates top-4) | **Accurate** |

**Summary: 4/5 accurate, 1/5 partially accurate.** Retrieval was relevant on all
five (each question's expected source appeared at rank 1 in Milestone-4 testing).
Notably, Q4 demonstrated the authority-weighting rule working: the model surfaced
both the law source (#7) and the lease (#9) and explicitly deferred to the law.

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** Q3 — *"As an international student with no U.S. credit
history, what document can I use to help secure an off-campus apartment?"*
(Expected: the I-20 form.)

**What the system returned:** *"…you may be requested to show other forms of
funding documentation to be approved for an off-campus apartment if you don't
have an I-20… many landlords will require a co-signer… **However, it is not
explicitly stated what specific document you can use** to help secure an
off-campus apartment [1]."* The system mentioned the I-20 but explicitly declined
to commit to it as the answer.

**Root cause (tied to a specific pipeline stage):** This is a **generation-stage**
failure caused by the interaction between source phrasing and the grounding
prompt — *not* a retrieval failure. Retrieval worked correctly: source #4, which
contains the I-20 fact, was returned at rank 1. But source #4 states the fact
**negatively/indirectly**: *"Without an I-20, you may be requested to show other
forms of funding documentation to be approved."* It never says the affirmative
*"use your I-20 to secure an apartment."* Because the system prompt forbids
inferring beyond the literal text, the model — behaving exactly as instructed —
refused to assert the affirmative claim the question asked for, and hedged
instead. The strict grounding that makes the system trustworthy on out-of-domain
questions is the same constraint that made it under-answer here.

**A second, retrieval-stage failure worth noting:** a terse paraphrase of Q1,
*"What is the No More Than Four rule?"* (dropping "Boston" / "student renters"),
**fails at retrieval** — the answer-bearing source #8 does not appear in the
top-6 at all. The phrase "no more than four" embeds close to the GBREB lease's
clause enumeration, and without the disambiguating context words ("Boston,"
"students," "unrelated"), the lease chunks (#9) out-rank the zoning page. The
system then correctly **refuses** rather than answering from the wrong chunks —
grounding working as designed, but on incomplete retrieval.

**What you would change to fix it:** For Q3, soften the prompt to allow
*direct paraphrase* of a passage (so "without an I-20 you'll need other funding
docs" can be answered as "the I-20 is the key document") while still forbidding
outside knowledge — or add a light query-expansion / HyDE step so the question's
intent ("what document proves I can pay") better matches the passage's negative
phrasing. For the terse-query retrieval miss, add **query expansion** (append
domain context like "Boston housing") or a **hybrid retriever** (BM25 keyword +
dense embedding) so a distinctive phrase like "No More Than Four" is matched
lexically even when the dense embedding is ambiguous.

---

## Spec Reflection

**One way the spec helped you during implementation:** Writing the Retrieval
Approach section in `planning.md` *before* coding forced me to confront
all-MiniLM-L6-v2's 256-token limit up front, and that single constraint
propagated cleanly through the whole build. It set the ~240-token chunk target,
which I then enforced by measuring length in real model word-pieces rather than
characters, and the chunker verifies it (0/267 chunks exceed the limit, so
nothing is silently truncated at embedding time). Without having reasoned about
the embedding model in the spec first, I would likely have chunked by character
count and lost the tails of long legal clauses — exactly the kind of bug that is
invisible until evaluation. The spec turned a downstream landmine into an
up-front design parameter.

**One way your implementation diverged from the spec, and why:** Two divergences.
First, my `planning.md` Architecture diagram named the **Claude API** for
generation, but the implementation uses the **Groq API** — the starter repo is
provisioned for Groq (`GROQ_API_KEY` in `.env`, `groq` pinned in
`requirements.txt`, free key), so using what was actually available was the
pragmatic choice. Second, and more substantively, the spec implied I would
**filter low-relevance chunks** with a cosine-similarity threshold before
generation. I implemented this, then removed it as a grounding gate after
calibration data proved it was unsound: an out-of-domain query ("best pizza in
Boston," ~0.43) scored *higher* than a valid short in-domain question (~0.30),
because shared tokens like "Boston" inflate similarity. No absolute threshold
could separate relevant from irrelevant, so I moved grounding enforcement
entirely to the LLM's system prompt (which refuses based on *meaning*, not score)
and kept the threshold only as an optional tunable knob. The spec's instinct was
right; the data showed the mechanism had to change.

---

## AI Usage

**Instance 1 — Chunking implementation**

- *What I gave the AI:* My `planning.md` Chunking Strategy section (~240-token
  target, ~15% overlap, structure-aware splitting, the 256-token model limit) and
  asked it to implement `chunk_text()` plus a chunker that reads the cleaned docs
  and writes metadata-tagged chunks.
- *What it produced:* A recursive paragraph→sentence→word splitter that, crucially,
  measures chunk length using the **real all-MiniLM-L6-v2 tokenizer** rather than
  the character-count approximation my spec had loosely referenced (LangChain's
  `RecursiveCharacterTextSplitter`). It also produced a verification report
  asserting no chunk exceeds the model limit.
- *What I changed or overrode:* I **directed it away from a character-based
  splitter** (which can't guarantee the token limit that is the entire reason for
  the 240 target) toward token-accurate measurement, and accepted that as an
  intentional divergence from the spec. I also had it carry overlap as whole
  trailing *sentences* rather than a raw character window, so chunks never start
  mid-sentence.

**Instance 2 — Grounded generation + attribution**

- *What I gave the AI:* My grounding requirement (answers from retrieved context
  only, with source attribution), the desired output format (answer + source
  list), the Gradio skeleton, and an instruction to make grounding *enforced* and
  attribution *programmatic*, then to review the code before running it.
- *What it produced:* A `generate.answer()` that builds a grounded prompt, calls
  the LLM, and a Gradio UI. The first version had two bugs the review caught: (a)
  inline `[n]` citations numbered *passages* while the Sources list deduped by
  *document*, so the numbers didn't line up; and (b) an absolute similarity floor
  that falsely refused valid short questions.
- *What I changed or overrode:* I **overrode the citation numbering** to label
  passages by their source number so inline `[n]` aligns with the Sources list;
  **removed the similarity floor as a grounding gate** after the calibration test
  above and moved grounding to the system prompt; and **tightened attribution** to
  list only the sources the answer actually cited (filtering by emitted `[n]`),
  rather than every retrieved chunk, so the source list doesn't over-claim. I also
  overrode the suggested `gradio>=6.9.0` dependency down to `gradio 5.x`, because
  gradio 6 requires `huggingface-hub>=1.2`, which conflicts with
  sentence-transformers/transformers (`<1.0`) and breaks the embedding stack.
