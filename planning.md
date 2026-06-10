# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

The domain I chose is "Student Housing".
The student housing domain for Northeastern University encompasses complex leasing rules, international student requirements, and localized Boston zoning laws. This knowledge is highly fragmented across official university PDFs, strict legal state documents, and informal crowd-sourced student forums, making it difficult for students to find definitive, synthesized answers when navigating the off-campus housing market.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Northeastern Off-Campus Housing Guidelines | This is the official university portal. Scraping it gives the RAG knowledge of the university's recommended search process, verified property lister guidelines, and "Lease Genius" checklist tools. | https://offcampus.housing.northeastern.edu/explore-housing-options/bostonareahousing/ |
| 2 | Northeastern Guide to Residence Hall Living (PDF) | This is the definitive rulebook for on-campus living. It holds the exact administrative answers to lockout fees, guest policies, move-out dates, and RA protocols. | https://housing.northeastern.edu/wp-content/uploads/2025/08/Guide-to-Residence-Hall-Living-AY25-26-Final.pdf |
| 3 | Office of Global Services (OGS) Housing Guide | Essential for the international demographic. It outlines summer storage options, temporary housing recommendations upon arrival, and scam avoidance specifically tailored to students arriving from abroad. | https://international.northeastern.edu/ogs/housing/ |
| 4 | Network Housing Relocation - International Resources | Details the documentation required for renting without a U.S. credit score, including how to use an I-20 form in place of standard financial documents to secure an off-campus apartment. | https://network.housing.northeastern.edu/relocation-resources/resources-for-international-students/ |
| 5 | r/NEU Housing & Roommate Megathread | Unstructured community data. It captures student sentiment, current market pricing for sublets, warnings about specific management companies, and real-world advice on dorm lotteries. | https://www.reddit.com/r/NEU/ |
| 6 | r/boston Housing Wiki | A massive, crowd-sourced guide to the Boston rental market. It provides neighborhood breakdowns, broker fee avoidance strategies, and standard moving logistics. | https://www.reddit.com/r/boston/wiki/housing/ |
| 7 | Massachusetts Attorney General's Guide to Landlord and Tenant Rights (PDF) | Grounds your RAG in state law. It contains the legal facts regarding security deposit limits, eviction notices, and habitability requirements (heating season rules, pest control). | https://www.mass.gov/doc/2025-guide-to-landlord-tenant-rights-11182025/download |
| 8 | Northeastern Leasing Information & Boston Zoning Rules | Details the "No More Than Four" rule a strict City of Boston zoning ordinance prohibiting more than four unrelated undergraduate students from living together. | https://offcampus.housing.northeastern.edu/get-started/leasing-information/ |
| 9 | Standard Greater Boston Real Estate Board (GBREB) Lease (PDF) | Processing a blank standard lease template allows your system to understand what a standard clause looks like when a user asks about normal landlord fees. | https://www.brandeis.edu/graduate-affairs/housing/docs/sample-lease-fixed-terms.pdf |
| 10 | MBTA Subway Map and Schedules | Commute time is a major factor for off-campus students. Indexing transit data allows the RAG to answer queries about which neighborhoods are directly connected to the main campus. | https://www.mbta.com/schedules/subway |

---

## Chunking Strategy

For our mixed media sources, we will use a hybrid chunking approach that matches the data type:

* **The 3 PDFs:** I'll be using Recursive Character Splitting with a chunk size of ~500 tokens (roughly 350-400 words) and a 10-20% overlap (e.g., 50-100 tokens). This breaks down the dense legal and administrative information while preserving cross-boundary context.
* **The 6 Standard Web Pages (URLs & Wiki):** I'll be using Structure-Aware Chunking. Parse the HTML to extract headings (H1, H2, H3), lists, and paragraphs. Treat each major section as its own chunk, maintaining the site’s natural hierarchy rather than splitting arbitrarily.
* **The 1 Subreddit Thread:** I'll be using Thread-Based/Comment-Aware Chunking. We will not split the original post and its comments haphazardly. Group the main post and each sub-comment chain into an isolated, standalone "document block.

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
all-MiniLM-L6-v2 via sentence-transformers

**Top-k:**
k = 8

**Production tradeoff reflection:**
Context Length: The current local model (all-MiniLM-L6-v2) has a very limited context window (typically 256-512 tokens). If cost were not an issue, upgrading to a model like OpenAI's text-embedding-3-large (which handles up to 8,192 tokens) would be highly beneficial.

Multilingual Support: Because this RAG specifically targets the Office of Global Services (OGS) and international student resources, multilingual support is a massive factor. A commercial multilingual model would allow incoming international students to query the system in their native language (e.g., Mandarin, Spanish, Hindi) and successfully retrieve answers accurately grounded in the English source documents.

Accuracy on Domain-Specific Text: My data mixes strict legal/administrative jargon ("joint and several liability," "I-20 forms") with hyper-local Boston student slang ("Allston Christmas," "dorm lottery"). A more robust, parameter-heavy model would possess a much deeper semantic understanding of these localized real estate and university concepts compared to a small, generalized open-source model.

Latency vs. Reliability: The major downside of switching to a massive commercial model is network latency. On peak dates like September 1st (moving day), a spike in student queries could cause API timeouts or slow response times. A small local model like MiniLM trades deep comprehension for guaranteed, near-zero latency.
---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | According to the Northeastern Leasing Information, what is the "No More Than Four" rule? | It is a City of Boston zoning ordinance that prohibits more than four unrelated undergraduate students from living together in a single apartment or house. |
| 2 | Based on the Network Housing Relocation resources, what specific document can international students without a U.S. credit score use to help secure an off-campus apartment? | They can use their I-20 form in place of standard financial documents. |
| 3 | According to the Massachusetts Attorney General's Guide to Landlord and Tenant Rights, what is the legally allowed maximum amount a landlord can charge for a security deposit? | The security deposit cannot exceed the amount of one month's rent. |
| 4 | Based on the r/boston Housing Wiki, what is the local nickname given to the September 1st moving day phenomenon where discarded furniture lines the neighborhood sidewalks? | "Allston Christmas" |
| 5 | According to the MBTA Subway Map and schedules, which specific branch of the Green line directly connects to the main Northeastern campus? | The Green Line "E" Branch. |

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
