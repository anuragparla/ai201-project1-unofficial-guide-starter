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
| 9 | Standard Greater Boston Real Estate Board (GBREB) Lease (PDF) | Processing a blank standard lease template allows your system to understand what a standard clause looks like when a user asks about normal landlord fees. | https://freeforms.com/wp-content/uploads/2021/04/Greater-Boston-Real-Estate-Board-Standard-Form-Apartment-Lease.pdf |
| 10 | MBTA Subway Map and Schedules | Commute time is a major factor for off-campus students. Indexing transit data allows the RAG to answer queries about which neighborhoods are directly connected to the main campus. | https://www.mbta.com/schedules/subway |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

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
