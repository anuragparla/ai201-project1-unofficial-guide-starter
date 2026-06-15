"""Milestone 5 interface: a Gradio front-end over the grounded generator.

The UI is a thin shell — all grounding and attribution logic lives in
generate.answer(). Following the recommended two-output layout: the answer and
its source list are shown in separate boxes.

Run:
    python -m src.generation.app
then open the printed local URL (http://127.0.0.1:7860).
"""

import gradio as gr

from ..retrieval import config
from .generate import answer

TITLE = "The Unofficial Guide — NEU Student Housing"
DESCRIPTION = (
    "Ask about Northeastern / Boston student housing: leases, the "
    '"No More Than Four" rule, security deposits, international-student '
    "documents, the T, and more. Answers come **only** from the indexed "
    "sources, with attribution. If the sources don't cover it, the assistant "
    "says so rather than guessing."
)

EXAMPLES = [
    'What is Boston\'s "No More Than Four" rule?',
    "What is the maximum security deposit a landlord can charge in Massachusetts?",
    "As an international student with no U.S. credit, what document helps me rent?",
    "Who pays for heat and hot water in a Massachusetts rental?",
    "Which T line connects to Northeastern's main campus?",
]


def handle_query(question: str):
    """Return (answer_text, sources_text) for the two output boxes."""
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""
    result = answer(question, k=config.TOP_K)
    if not result.sources:
        sources = "(no sources — this question isn't covered by the indexed corpus)"
    else:
        sources = "\n".join(
            f"• [{s['n']}] {s['source']} ({s['doc_type']}) — {s['url']}"
            for s in result.sources
        )
    return result.text, sources


def build_demo():
    with gr.Blocks(title=TITLE) as demo:
        gr.Markdown(f"# {TITLE}")
        gr.Markdown(DESCRIPTION)
        inp = gr.Textbox(
            label="Your question",
            placeholder="e.g. How many unrelated students can share an apartment in Boston?",
            lines=2,
        )
        btn = gr.Button("Ask", variant="primary")
        answer_box = gr.Textbox(label="Answer", lines=8)
        sources_box = gr.Textbox(label="Sources", lines=4)
        gr.Examples(EXAMPLES, inputs=inp)

        btn.click(handle_query, inputs=inp, outputs=[answer_box, sources_box])
        inp.submit(handle_query, inputs=inp, outputs=[answer_box, sources_box])
    return demo


def main():
    build_demo().launch()


if __name__ == "__main__":
    main()
