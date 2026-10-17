"""Generates every SVG figure in ../ (run: python images/src/figures.py).

Each function draws one figure and returns a Fig; FIGURES maps file names to
functions. Figures are original drawings for this guide.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import INK, KINDS, MUTED, RED, Fig  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FIGURES: dict[str, callable] = {}


def figure(name):
    def deco(fn):
        FIGURES[name] = fn
        return fn
    return deco


# --------------------------------------------------------------------------
# Front matter
# --------------------------------------------------------------------------
@figure("cover.svg")
def cover():
    f = Fig(960, 380, desc="Cover: GraphRAG, Illustrated - knowledge-graph RAG with ArangoDB and AQL. "
                           "A question flows through a small knowledge graph to a grounded answer.")
    f.text(40, 92, "GraphRAG,", size=50, weight="bold")
    f.text(40, 150, "Illustrated", size=50, weight="bold", color=KINDS["db"][1])
    f.text(42, 192, "Knowledge-graph RAG with ArangoDB & AQL", size=21, color=MUTED)
    f.hand(42, 238, "vectors find what sounds similar...", size=19, color=INK)
    f.hand(42, 266, "graphs find what is actually connected.", size=19, color=RED)
    f.text(42, 330, "An illustrated study guide to the design & architecture in Essential GraphRAG",
           size=14, color=MUTED, italic=True)
    f.text(42, 351, "(Bratanič & Hane, Manning 2025), with every Neo4j/Cypher example rebuilt for ArangoDB.",
           size=14, color=MUTED, italic=True)
    # little graph doodle on the right (edges first, nodes on top)
    f.box(560, 40, 170, 50, "Who mentored", "Telemachus?", kind="user", size=14, sub_size=14)
    n1, n2, n3, n4 = (650, 178, 26), (812, 128, 26), (872, 252, 22), (566, 262, 20)
    f.edge(n2, n1, "mentors", curve=0.15, label_dy=-4)
    f.edge(n1, n3, "son of", label_dx=14, label_dy=-8)
    f.edge(n1, n4, "son of", label_dx=-44, label_dy=-10)
    f.edge(n2, n3, "protects", curve=-0.2, label_dx=10)
    f.node(*n1, label="TELEMACHUS", kind="db")
    f.node(*n2, label="MINERVA", kind="llm")
    f.node(*n3, label="ULYSSES", kind="db")
    f.node(*n4, label="PENELOPE", kind="db")
    f.arrow(645, 92, 650, 148, color=RED, width=2)
    f.hand(664, 122, "start here", size=14)
    f.note(760, 300, "AQL inside!", w=120, size=16, rot=4)
    return f


@figure("roadmap.svg")
def roadmap():
    f = Fig(960, 560, "The road through this guide",
            "from \"the LLM is guessing\" to \"an evaluated, agentic GraphRAG system\"",
            desc="Roadmap of the nine chapters as stops on a winding road: unstructured retrieval "
                 "(chapters 2-3), querying structure (4-5), building graphs (6-7), evaluation (8), "
                 "big picture (9).")
    # road
    road = ("M80,150 L860,150 Q910,150 910,200 L910,270 Q910,320 860,320 L120,320 "
            "Q70,320 70,370 L70,440 Q70,490 120,490 L880,490")
    f.raw(f'<path d="{road}" fill="none" stroke="#d9d2c3" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>')
    f.raw(f'<path d="{road}" fill="none" stroke="#fff" stroke-width="3" stroke-dasharray="14 12"/>')
    stops = [
        (150, 150, "1", "Why LLMs need help", "RAG + knowledge graphs", "gray"),
        (450, 150, "2", "Vector & hybrid search", "APPROX_NEAR_COSINE + BM25", "doc"),
        (750, 150, "3", "Smarter vector retrieval", "step-back + parent docs", "doc"),
        (780, 320, "4", "text2aql", "the LLM writes AQL", "search"),
        (480, 320, "5", "Agentic RAG", "router, tools, critic", "search"),
        (180, 320, "6", "Build KGs with LLMs", "structured outputs → UPSERT", "db"),
        (200, 490, "7", "Microsoft GraphRAG", "communities, global & local", "db"),
        (500, 490, "8", "Evaluation", "recall, faithfulness, correctness", "user"),
        (790, 490, "9", "The big picture", "which retriever when?", "llm"),
    ]
    for x, y, n, title, sub, kind in stops:
        fill, stroke = KINDS[kind]
        f.raw(f'<circle cx="{x}" cy="{y}" r="20" fill="{stroke}" stroke="#fff" stroke-width="3"/>')
        f.text(x, y + 6, n, size=17, anchor="middle", color="#fff", weight="bold")
        f.text(x, y - 34, title, size=16, anchor="middle", weight="bold", halo=True)
        f.text(x, y + 44, sub, size=13, anchor="middle", color=MUTED, halo=True)
    f.hand(560, 238, "unstructured text  ➜  queries over structure", size=15, color=MUTED, anchor="middle")
    f.hand(470, 410, "build the graph  ➜  measure it", size=15, color=MUTED, anchor="middle")
    return f


# --------------------------------------------------------------------------
# Chapter 1
# --------------------------------------------------------------------------
@figure("ch01-llm-limits.svg")
def ch01_llm_limits():
    f = Fig(960, 470, "Four ways a lone LLM goes wrong",
            "it only knows what was baked into its weights at training time",
            desc="A timeline of public training text ends at the knowledge cutoff; later events and "
                 "private company data never reach the model's weights, which leads to cutoff gaps, "
                 "outdated answers, confident hallucinations and ignorance of private facts.")
    # timeline
    f.raw('<rect x="60" y="110" width="520" height="34" rx="8" fill="#fff3d4" stroke="#a87500" stroke-width="2"/>')
    f.text(320, 133, "public text the model was trained on", size=15, anchor="middle", weight="bold")
    f.raw('<rect x="600" y="110" width="300" height="34" rx="8" fill="#f2efe8" stroke="#8b8578" '
          'stroke-width="2" stroke-dasharray="7 5"/>')
    f.text(750, 133, "the world keeps changing...", size=15, anchor="middle", color=MUTED)
    f.raw('<line x1="590" y1="96" x2="590" y2="160" stroke="#c0392b" stroke-width="3" stroke-dasharray="6 4"/>')
    f.hand(590, 92, "knowledge cutoff", size=15, anchor="middle")
    # llm
    f.arrow(250, 146, 250, 214, label="training (months, $$$)", label_dx=78)
    f.llm(170, 216, 160, 74, "LLM", "frozen weights")
    # private vault
    f.box(700, 210, 220, 80, "Your private data", "contracts, tickets, wikis, DBs", kind="gray")
    f.raw('<rect x="895" y="198" width="26" height="22" rx="4" fill="#8b8578"/>'
          '<path d="M900,198 v-7 a8,8 0 0 1 16,0 v7" fill="none" stroke="#8b8578" stroke-width="3"/>')
    f.arrow(698, 252, 338, 252, color=RED, dashed=True, label="never seen", size=14)
    f.text(520, 249, "✕", size=26, anchor="middle", color=RED, weight="bold")
    # answers
    items = [
        (1, "Cutoff", "\"I have no information after my training date.\""),
        (2, "Outdated", "\"Mark Cuban owns the Dallas Mavericks.\" (was true once)"),
        (3, "Hallucination", "\"Its WikiData ID is Q152232.\" (confident & wrong)"),
        (4, "No private data", "\"I can't see your Q3 supplier contract.\""),
    ]
    for i, (n, title, quote) in enumerate(items):
        y = 330 + i * 32
        f.badge(80, y - 5, n)
        f.text(102, y, title, size=15, weight="bold")
        f.text(250, y, quote, size=14, color=MUTED, italic=True)
    f.poly([(250, 292), (250, 312)], color=INK)
    f.note(690, 330, "Fix: put the facts in the prompt at question time (RAG) - and keep them in a graph.",
           w=240, size=14, rot=2)
    return f


@figure("ch01-finetune-vs-rag.svg")
def ch01_finetune_vs_rag():
    f = Fig(960, 470, "Two ways to give an LLM new facts",
            "change its weights... or hand it the facts with every question",
            desc="Left: supervised finetuning feeds question/answer pairs through training to change the "
                 "weights - slow and unreliable for new facts. Right: retrieval-augmented generation looks up "
                 "relevant facts at question time and puts them into the prompt.")
    # left
    f.text(240, 108, "Supervised finetuning", size=18, weight="bold", anchor="middle")
    f.box(60, 130, 360, 64, "Q: Who won the 2023 NBA title?", "A: the Denver Nuggets", kind="doc", size=14)
    f.arrow(240, 196, 240, 240, label="training run", label_dx=56)
    f.llm(165, 244, 150, 70, "LLM", "weights nudged")
    f.note(60, 344, "Slow & costly to repeat. Studies disagree on whether new facts even stick.",
           w=360, size=14, rot=-1)
    # divider
    f.raw('<line x1="480" y1="100" x2="480" y2="440" stroke="#e3d9c6" stroke-width="2" stroke-dasharray="4 6"/>')
    # right
    f.text(720, 108, "Retrieval-augmented generation (RAG)", size=18, weight="bold", anchor="middle")
    f.person(540, 140, 0.8, label="")
    f.box(580, 128, 150, 40, "question", kind="user", size=14)
    f.arrow(732, 148, 790, 148, label="search")
    f.cylinder(792, 118, 140, 72, "knowledge", "base", size=14)
    f.arrow(862, 192, 862, 228, label="relevant facts", label_dx=-62)
    f.code(520, 232, 420, ["Use only this context:", "  {context}", "Question: {question}"],
           title="PROMPT TEMPLATE", size=13, hl=False)
    f.arrow(730, 334, 730, 362)
    f.llm(655, 364, 150, 56, "LLM", "")
    f.arrow(807, 392, 868, 392)
    f.box(870, 372, 72, 40, "answer", kind="ok", size=13)
    f.hand(530, 440, "fresh, private, citable - no retraining", size=15, color=KINDS["ok"][1])
    return f


@figure("ch01-kg-in-arango.svg")
def ch01_kg_in_arango():
    f = Fig(960, 500, "One database, both kinds of data",
            "unstructured text (with an embedding) linked to structured facts - in ArangoDB terms",
            desc="An article document with text and embedding in the articles collection mentions a company; "
                 "the company has a CEO and employees; an employee is assigned a task. Each edge is a document "
                 "in an edge collection with _from and _to.")
    f.raw('<rect x="30" y="96" width="280" height="380" rx="16" fill="#fffaf0" stroke="#e3d9c6" stroke-width="2"/>')
    f.raw('<rect x="330" y="96" width="600" height="380" rx="16" fill="#f6fbf2" stroke="#e3d9c6" stroke-width="2"/>')
    f.hand(46, 122, "unstructured", size=16, color=KINDS["doc"][1])
    f.hand(346, 122, "structured", size=16, color=KINDS["db"][1])
    art = (170, 250, 36)
    comp = (520, 250, 34)
    ceo = (700, 150, 30)
    emp = (700, 345, 30)
    task = (870, 250, 30)
    f.edge(art, comp, "mentions", label_dy=-10)
    f.edge(comp, ceo, "has_ceo", label_dx=-30, label_dy=-6)
    f.edge(emp, comp, "employee_of", label_dx=-34, label_dy=10)
    f.edge(emp, ceo, "reports_to", label_dx=42)
    f.edge(task, emp, "assigned_to", label_dx=34, label_dy=10)
    f.node(*art, label="articles/a1", kind="doc")
    f.node(*comp, label="companies/northwind", kind="db")
    f.node(*ceo, label="persons/maya", kind="user")
    f.node(*emp, label="persons/leo", kind="user")
    f.node(*task, label="tasks/t7", kind="search")
    f.code(48, 316, 248, ['{ "title": "GraphLens 2.0 ships",', '  "date": "2025-07-07",',
                          '  "text": "Northwind ...",', '  "embedding": [0.12, ...] }'],
           size=12, dark=False, hl=False)
    f.code(560, 408, 220, ['{ "_from": "persons/leo",', '  "_to": "companies/northwind",',
                           '  "since": "2023-01-01" }'], size=11, dark=False, hl=False, pad=8)
    f.code(780, 130, 140, ['{ "title": "Release',
                           '  new model",', '  "status":', '  "completed" }'],
           size=11, dark=False, hl=False, pad=8)
    return f


@figure("ch01-neo4j-to-arango.svg")
def ch01_neo4j_to_arango():
    f = Fig(960, 430, "Same graph, different vocabulary",
            "how the book's Neo4j property graph maps onto ArangoDB",
            desc="A Neo4j node with a label and properties becomes a JSON document in a document collection, "
                 "identified by _key and _id. A typed relationship with properties becomes a document in an "
                 "edge collection with _from and _to pointing at the two vertex documents.")
    f.text(240, 106, "Neo4j / Cypher", size=18, weight="bold", anchor="middle")
    f.text(710, 106, "ArangoDB / AQL", size=18, weight="bold", anchor="middle")
    a, b = (120, 190, 34), (360, 190, 34)
    f.edge(a, b, "ACTED_IN {roles}", label_dy=-12)
    f.node(*a, label=":Person", kind="user", label_pos="below")
    f.node(*b, label=":Movie", kind="doc", label_pos="below")
    f.text(120, 262, "{name: 'Tom Hanks'}", size=12, anchor="middle", color=MUTED, font="mono")
    f.text(360, 262, "{title: 'Cast Away'}", size=12, anchor="middle", color=MUTED, font="mono")
    f.code(520, 130, 200, ['// persons', '{ "_key": "Tom_Hanks",', '  "_id": "persons/Tom_Hanks",',
                           '  "name": "Tom Hanks" }'], size=11, dark=False, hl=False, pad=9)
    f.code(740, 130, 200, ['// movies', '{ "_key": "Cast_Away",', '  "_id": "movies/Cast_Away",',
                           '  "title": "Cast Away" }'], size=11, dark=False, hl=False, pad=9)
    f.code(600, 262, 270, ['// acted_in  (edge collection)', '{ "_from": "persons/Tom_Hanks",',
                           '  "_to": "movies/Cast_Away",', '  "roles": ["Chuck Noland"] }'],
           size=11, dark=False, hl=False, pad=9)
    f.arrow(640, 260, 625, 222, color=KINDS["db"][1], width=1.6)
    f.arrow(830, 260, 840, 222, color=KINDS["db"][1], width=1.6)
    rows = [("node label", "document collection"), ("relationship type", "edge collection"),
            ("property", "attribute (JSON)"), ("node id", "_id = collection/_key")]
    for i, (l, r) in enumerate(rows):
        y = 318 + i * 26
        f.text(196, y, l, size=14, anchor="end")
        f.text(220, y, "→", size=16, anchor="middle", color=RED)
        f.text(244, y, r, size=14, color=KINDS["db"][1], weight="bold")
    return f


# --------------------------------------------------------------------------
# Chapter 2
# --------------------------------------------------------------------------
@figure("ch02-two-stages.svg")
def ch02_two_stages():
    f = Fig(960, 470, "Vector RAG has two stages",
            "data setup happens once; query time happens on every question",
            desc="Data setup: paper text is chunked, embedded and stored in an ArangoDB chunks collection with a "
                 "vector index and a search view. Query time: the question is embedded with the same model, the "
                 "vector index returns the nearest chunks, and the LLM answers from them.")
    f.text(40, 112, "DATA SETUP", size=14, weight="bold", color=KINDS["doc"][1])
    f.doc(48, 128, 52, 64, label="paper.pdf")
    f.arrow(108, 160, 160, 160)
    f.box(162, 128, 150, 64, "chunk_text()", "500 chars, 40 overlap", kind="doc", size=15)
    f.arrow(314, 160, 366, 160)
    f.box(368, 128, 160, 64, "embedding model", "text -> 1536 numbers", kind="llm", size=15)
    f.arrow(530, 160, 600, 160, label="INSERT")
    f.cylinder(602, 112, 320, 104, "ArangoDB", "chunks {index, text, embedding} + vector index + search view",
               size=15)
    # query time
    f.text(40, 286, "QUERY TIME", size=14, weight="bold", color=KINDS["user"][1])
    f.person(64, 314, 0.8)
    f.box(96, 302, 150, 56, "question", kind="user", size=15)
    f.arrow(248, 330, 300, 330)
    f.box(302, 302, 160, 56, "embedding model", "same one!", kind="llm", size=15)
    f.arrow(464, 330, 520, 330, label="vector")
    f.box(522, 296, 200, 68, "APPROX_NEAR_COSINE", "top-k most similar chunks", kind="search", size=14)
    f.arrow(762, 218, 642, 294, label="uses the index", label_dx=40)
    f.arrow(724, 330, 776, 330)
    f.llm(778, 300, 110, 60, "LLM", "")
    f.arrow(832, 362, 832, 400)
    f.box(752, 402, 160, 44, "grounded answer", kind="ok", size=14)
    f.arrow(380, 300, 446, 194, color=RED, dashed=True, both=True)
    f.hand(60, 232, "embed questions and chunks with the", size=14)
    f.hand(60, 252, "SAME model, or the vectors don't match", size=14)
    f.hand(300, 420, "the generator can be a smaller model: the retriever already did the knowing",
           size=14, color=MUTED)
    return f


@figure("ch02-chunking.svg")
def ch02_chunking():
    f = Fig(960, 330, "Sliding-window chunking",
            "fixed-size windows that overlap a little and only cut at spaces",
            desc="A long text strip is cut into windows of about 500 characters. Each window starts about 40 "
                 "characters before the previous one ended, so text on a boundary appears in both chunks, and "
                 "window edges are moved to the nearest space so words are not split.")
    # text strip with words
    x0, y0, w = 40, 160, 880
    f.raw(f'<rect x="{x0}" y="{y0}" width="{w}" height="36" rx="6" fill="#fff" stroke="#b9b2a2" stroke-width="1.5"/>')
    import random
    rnd = random.Random(3)
    x = x0 + 8
    while x < x0 + w - 20:
        ww = rnd.randint(14, 46)
        f.raw(f'<rect x="{x}" y="{y0 + 14}" width="{min(ww, x0 + w - 12 - x)}" height="8" rx="3" fill="#d8d1c2"/>')
        x += ww + 8
    windows = [(40, 360, "chunk 1", "doc"), (318, 650, "chunk 2", "search"), (608, 920, "chunk 3", "db")]
    for i, (a, b, label, kind) in enumerate(windows):
        fill, stroke = KINDS[kind]
        y = 112 if i % 2 == 0 else 212
        h = 38
        f.raw(f'<rect x="{a}" y="{y if i % 2 == 0 else y0 + 52}" width="{b - a}" height="{h}" rx="8" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="2" opacity="0.95"/>')
        ty = (y if i % 2 == 0 else y0 + 52) + 25
        f.text((a + b) / 2, ty, label, size=15, anchor="middle", weight="bold")
        f.raw(f'<line x1="{a}" y1="{y0 - 6}" x2="{a}" y2="{y0 + 42}" stroke="{stroke}" stroke-width="2" stroke-dasharray="4 3"/>')
        f.raw(f'<line x1="{b}" y1="{y0 - 6}" x2="{b}" y2="{y0 + 42}" stroke="{stroke}" stroke-width="2" stroke-dasharray="4 3"/>')
    for a, b in ((318, 360), (608, 650)):
        f.raw(f'<rect x="{a}" y="{y0}" width="{b - a}" height="36" fill="{RED}" opacity="0.18"/>')
    f.hand(339, 300, "overlap (~40 chars): a sentence on the", size=14, anchor="middle")
    f.hand(339, 318, "border lands in both chunks", size=14, anchor="middle")
    f.arrow(339, 284, 339, 252, color=RED)
    f.hand(800, 300, "edges snap to spaces: no half-words", size=14, anchor="middle")
    f.arrow(800, 284, 650, 252, color=RED, curve=-20)
    f.text(40, 98, "size ≈ 500 characters", size=13, color=MUTED, italic=True)
    return f


def _clip(poly, a, b, c):
    """Keep the part of polygon `poly` where a*x + b*y <= c."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        pin = a * p[0] + b * p[1] <= c
        qin = a * q[0] + b * q[1] <= c
        if pin:
            out.append(p)
        if pin != qin:
            t = (c - a * p[0] - b * p[1]) / (a * (q[0] - p[0]) + b * (q[1] - p[1]))
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


@figure("ch02-vector-index.svg")
def ch02_vector_index():
    f = Fig(960, 545, "How vector search finds \"similar\"",
            "cosine similarity, and how ArangoDB's IVF vector index avoids comparing against everything",
            desc="Left: chunks and the question are points; similarity is the cosine of the angle between "
                 "their vectors. Right: an IVF vector index groups vectors into cells around centroids (nLists); "
                 "a query only searches the nearest nProbe cells, which is fast but approximate - a true neighbour "
                 "just across a cell border can be missed.")
    # left: cosine
    ox, oy = 90, 430
    f.raw(f'<line x1="{ox}" y1="{oy}" x2="{ox + 360}" y2="{oy}" stroke="#b9b2a2" stroke-width="1.5"/>')
    f.raw(f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{oy - 320}" stroke="#b9b2a2" stroke-width="1.5"/>')
    pts = [(260, 170, "lab work"), (300, 205, "experiments"), (380, 330, "patents"), (220, 395, "Zurich"),
           (420, 380, "refrigerator")]
    q = (318, 160)
    for x, y, lab in pts:
        f.raw(f'<circle cx="{x}" cy="{y}" r="6" fill="{KINDS["doc"][0]}" stroke="{KINDS["doc"][1]}" stroke-width="2"/>')
        f.text(x + 10, y + 4, lab, size=12, color=MUTED)
    f.arrow(ox, oy, q[0], q[1], color=KINDS["user"][1], width=2.4)
    f.arrow(ox, oy, 260, 170, color=KINDS["doc"][1], width=2)
    f.arrow(ox, oy, 420, 380, color="#b9b2a2", width=1.6)
    import math
    a1 = math.atan2(oy - q[1], q[0] - ox)
    a2 = math.atan2(oy - 170, 260 - ox)
    r = 120
    f.raw(f'<path d="M{ox + r * math.cos(a1):.1f},{oy - r * math.sin(a1):.1f} '
          f'A {r} {r} 0 0 0 {ox + r * math.cos(a2):.1f},{oy - r * math.sin(a2):.1f}" '
          f'fill="none" stroke="{RED}" stroke-width="2.4"/>')
    f.hand(ox + 108, oy - 150, "small angle θ", size=14)
    f.hand(ox + 108, oy - 132, "= similar meaning", size=14)
    f.raw(f'<path d="M{q[0]},{q[1] - 11} l3,7 8,1 -6,5 2,8 -7,-4 -7,4 2,-8 -6,-5 8,-1 z" fill="{KINDS["user"][1]}"/>')
    f.text(q[0] + 12, q[1] - 6, "question", size=13, weight="bold", color=KINDS["user"][1])
    f.code(70, 96, 380, ["score = cos θ   (1 = same direction,", "               0 = unrelated)"],
           size=12, dark=False, hl=False, pad=8)
    # right: IVF cells
    X0, Y0, X1, Y1 = 520, 110, 930, 450
    cents = [(590, 170), (730, 150), (870, 200), (600, 360), (740, 300), (870, 390)]
    rect = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
    query = (700, 252)
    order = sorted(range(len(cents)), key=lambda i: (cents[i][0] - query[0]) ** 2 + (cents[i][1] - query[1]) ** 2)
    for i, (cx, cy) in enumerate(cents):
        poly = rect
        for j, (dx, dy) in enumerate(cents):
            if i == j:
                continue
            a, b = 2 * (dx - cx), 2 * (dy - cy)
            c = dx * dx + dy * dy - cx * cx - cy * cy
            poly = _clip(poly, a, b, c)
        fill = "#ffffff"
        if i == order[0]:
            fill = KINDS["search"][0]
        elif i == order[1]:
            fill = "#f0f6fd"
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in poly) + " Z"
        dash = ' stroke-dasharray="6 4"' if i == order[1] else ""
        stroke = KINDS["search"][1] if i in order[:2] else "#b9b2a2"
        f.raw(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>')
    import random
    rnd = random.Random(11)
    for cx, cy in cents:
        placed = 0
        while placed < 6:
            px, py = cx + rnd.uniform(-45, 45), cy + rnd.uniform(-38, 38)
            px, py = min(max(px, X0 + 8), X1 - 8), min(max(py, Y0 + 8), Y1 - 8)
            if (px - query[0]) ** 2 + (py - query[1]) ** 2 < 50 ** 2:
                continue  # keep the area around the question clear
            placed += 1
            f.raw(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{KINDS["doc"][0]}" stroke="{KINDS["doc"][1]}" stroke-width="1.6"/>')
        f.raw(f'<path d="M{cx - 7},{cy - 7} L{cx + 7},{cy + 7} M{cx - 7},{cy + 7} L{cx + 7},{cy - 7}" stroke="{INK}" stroke-width="2.4"/>')
    qx, qy = query
    f.raw(f'<path d="M{qx},{qy - 11} l3,7 8,1 -6,5 2,8 -7,-4 -7,4 2,-8 -6,-5 8,-1 z" fill="{KINDS["user"][1]}"/>')
    # a true neighbour just across the border of the probed cell
    nx_, ny_ = 690, 214
    f.raw(f'<circle cx="{nx_}" cy="{ny_}" r="5.5" fill="{RED}"/>')
    f.raw(f'<circle cx="{X0 + 6}" cy="523" r="5.5" fill="{RED}"/>')
    f.hand(X0 + 18, 528, "= the true nearest point, just across the border: missed when nProbe = 1", size=14)
    f.text(X0, 98, "IVF index: nLists cells,  × = centroid", size=13, color=MUTED)
    f.pill(X0, 482, "nProbe = 1: only the blue cell", kind="search", size=12)
    f.pill(X0 + 220, 482, "nProbe = 2: + the dashed cell", kind="search", size=12)
    return f


@figure("ch02-hybrid.svg")
def ch02_hybrid():
    f = Fig(960, 520, "Hybrid search = two rankings, made comparable, merged",
            "example numbers: divide each list by its best score, then keep each chunk once (MAX)",
            desc="Vector search returns cosine scores and BM25 keyword search returns unbounded scores. Each list "
                 "is divided by its own maximum so both top out at 1.0; the lists are merged and each chunk keeps its "
                 "highest normalized score; the top-k form the context.")
    vec = [("chunk 42", 0.82), ("chunk 44", 0.79), ("chunk 17", 0.71), ("chunk 31", 0.70)]
    kw = [("chunk 31", 7.4), ("chunk 42", 6.1), ("chunk 8", 5.2), ("chunk 44", 2.9)]

    def table(x, y, title, sub, rows, kind, fmt):
        f.box(x, y, 250, 50, title, sub, kind=kind, size=15)
        for i, (name, s) in enumerate(rows):
            yy = y + 74 + i * 30
            f.text(x + 14, yy, name, size=14, font="mono")
            f.text(x + 236, yy, fmt(s), size=14, font="mono", anchor="end")

    table(40, 100, "vector search", "APPROX_NEAR_COSINE", vec, "search", lambda s: f"{s:.2f}")
    table(40, 290, "keyword search", "ArangoSearch view + BM25", kw, "doc", lambda s: f"{s:.1f}")
    vmax, kmax = 0.82, 7.4
    table(360, 100, "÷ 0.82 (best vector)", "now 0..1", [(n, s / vmax) for n, s in vec], "search",
          lambda s: f"{s:.2f}")
    table(360, 290, "÷ 7.4 (best BM25)", "now 0..1", [(n, s / kmax) for n, s in kw], "doc",
          lambda s: f"{s:.2f}")
    f.arrow(292, 125, 356, 125)
    f.arrow(292, 315, 356, 315)
    merged = {}
    for n, s in vec:
        merged[n] = max(merged.get(n, 0), s / vmax)
    for n, s in kw:
        merged[n] = max(merged.get(n, 0), s / kmax)
    top = sorted(merged.items(), key=lambda t: -t[1])
    f.box(690, 190, 230, 50, "UNION → COLLECT", "MAX(score) per chunk", kind="ok", size=15)
    for i, (n, s) in enumerate(top):
        yy = 266 + i * 30
        keep = i < 4
        f.text(704, yy, n, size=14, font="mono", color=INK if keep else MUTED)
        f.text(906, yy, f"{s:.2f}", size=14, font="mono", anchor="end", color=INK if keep else MUTED)
        if not keep:
            f.raw(f'<line x1="700" y1="{yy - 5}" x2="910" y2="{yy - 5}" stroke="{RED}" stroke-width="1.5"/>')
    f.arrow(612, 150, 686, 210, curve=-10)
    f.arrow(612, 340, 686, 222, curve=10)
    f.hand(700, 440, "LIMIT 4: top-4 go to the LLM", size=14)
    f.hand(40, 500, "each list's #1 becomes 1.0 - that's why the top hybrid score is always 1.0", size=14, color=MUTED)
    return f


# --------------------------------------------------------------------------
# Chapter 3
# --------------------------------------------------------------------------
@figure("ch03-stepback.svg")
def ch03_stepback():
    f = Fig(960, 430, "Step-back prompting",
            "search with a broader question, answer the specific one",
            desc="The user's specific question is rewritten by an LLM into a broader step-back question; the "
                 "broader question is embedded and used for retrieval; the retrieved documents plus the ORIGINAL "
                 "question go to the LLM that writes the answer.")
    f.person(56, 130, 0.9)
    f.box(90, 112, 250, 70, "When was Einstein granted the", "patent for his blouse design?", kind="user",
          size=14, sub_size=14)
    f.arrow(342, 147, 392, 147)
    f.llm(394, 112, 170, 70, "LLM", "step-back prompt + examples")
    f.arrow(566, 147, 614, 147)
    f.box(616, 112, 300, 70, "What are some notable", "achievements in Einstein's life?", kind="search",
          size=14, sub_size=14)
    f.arrow(766, 184, 766, 236, label="embed + vector search", label_dx=-82)
    f.cylinder(676, 238, 180, 86, "parent docs", "broad context", size=15)
    f.arrow(674, 282, 470, 282, label="documents")
    f.llm(300, 250, 168, 64, "LLM", "writes the answer")
    f.arrow(216, 184, 300, 266, color=RED, dashed=True, label="original question", label_dx=-38, label_dy=6)
    f.arrow(300, 300, 190, 330)
    f.box(40, 318, 150, 54, "Oct 27, 1936", kind="ok", size=15)
    f.note(520, 336, "Broad queries match more of the text the answer hides in.", w=230, size=14, rot=2)
    return f


@figure("ch03-embedding-strategies.svg")
def ch03_embedding_strategies():
    f = Fig(960, 440, "Embed one thing, return another",
            "two ways to make vector matching sharper without losing context",
            desc="Left: the hypothetical-question strategy embeds questions an LLM generated for a document and "
                 "returns the document when a stored question matches. Right: the parent document retriever embeds "
                 "small child chunks and returns their whole parent document.")
    for x0, title in ((40, "Hypothetical questions"), (500, "Parent document retriever")):
        f.raw(f'<rect x="{x0}" y="92" width="420" height="324" rx="16" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
        f.text(x0 + 210, 122, title, size=17, weight="bold", anchor="middle")
    # left
    f.doc(70, 180, 70, 90, label="document")
    for i, q in enumerate(["What did she study at Berkeley?", "Where did she get her PhD?",
                           "When did she graduate?"]):
        y = 150 + i * 70
        f.box(232, y, 210, 50, q, "embedding ✓", kind="search", size=12, sub_size=11)
        f.arrow(142, 225, 230, y + 25, size=12)
    f.text(70, 340, "has_question", size=12, color=MUTED, italic=True)
    f.hand(60, 398, "match the user's question to stored questions, return the document", size=13)
    # right
    f.doc(530, 180, 70, 90, label="parent")
    for i, c in enumerate(["...master's in botany...", "...PhD from Yale...", "...in 1955..."]):
        y = 150 + i * 70
        f.box(700, y, 200, 50, c, "embedding ✓", kind="search", size=12, sub_size=11)
        f.arrow(602, 225, 698, y + 25, size=12)
    f.text(530, 340, "has_child", size=12, color=MUTED, italic=True)
    f.hand(520, 398, "match small, precise chunks; return the whole parent", size=13)
    return f


@figure("ch03-parent-retrieval.svg")
def ch03_parent_retrieval():
    f = Fig(960, 470, "Parent document retrieval in ArangoDB",
            "children are matched, parents are returned, each parent only once",
            desc="The pdfs collection links to parents via has_parent, and parents link to embedded children via "
                 "has_child. A query finds the k times 4 nearest children with APPROX_NEAR_COSINE, walks INBOUND "
                 "has_child to their parents, then COLLECTs to keep each parent once with its best score.")
    pdf = (440, 140, 30)
    parents = [(210, 250, 26), (440, 250, 26), (670, 250, 26)]
    kids = [(130, 370), (190, 370), (250, 370), (380, 370), (440, 370), (500, 370), (610, 370), (670, 370),
            (730, 370)]
    hits = {1, 2, 3, 4, 5, 7}
    for p in parents:
        f.edge(pdf, p, "")
    for i, (x, y) in enumerate(kids):
        p = parents[i // 3]
        f.edge(p, (x, y, 16), "", color=KINDS["search"][1] if i in hits else "#b9b2a2")
    f.node(*pdf, label="", kind="doc")
    f.text(480, 145, "pdfs/1709.00666", size=13, weight="bold")
    for i, p in enumerate(parents):
        f.node(*p, label="", kind="doc")
        f.text(p[0] + 32, p[1] + 5, f"parents/…-{i}", size=13, weight="bold")
    for i, (x, y) in enumerate(kids):
        fill = KINDS["search"][0] if i in hits else "#ffffff"
        stroke = KINDS["search"][1] if i in hits else "#b9b2a2"
        f.raw(f'<circle cx="{x}" cy="{y}" r="16" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    f.text(250, 188, "has_parent", size=13, color=MUTED, italic=True, halo=True)
    f.text(60, 318, "has_child", size=13, color=MUTED, italic=True)
    f.text(430, 418, "children: 500 chars + embedding", size=13, anchor="middle", color=MUTED)
    f.badge(800, 372, 1)
    f.text(822, 377, "6 children hit", size=14)
    f.badge(800, 252, 2)
    f.text(822, 257, "walk INBOUND", size=14)
    f.badge(800, 150, 3)
    f.text(822, 155, "COLLECT:", size=14)
    f.text(822, 173, "3 parents,", size=14)
    f.text(822, 191, "best score", size=14)
    f.hand(40, 452, "ask for k×4 children: several hits often share one parent, and we still want k parents", size=14)
    return f


# --------------------------------------------------------------------------
# Chapter 4
# --------------------------------------------------------------------------
@figure("ch04-movies-model.svg")
def ch04_movies_model():
    f = Fig(960, 430, "The Movies graph in ArangoDB",
            "2 document collections, 6 edge collections, 1 named graph (\"movies\")",
            desc="Document collections persons (133) and movies (38). Edge collections acted_in (with roles), "
                 "directed, produced, wrote and reviewed (with summary and rating) point from persons to movies; "
                 "follows points from persons to persons.")
    p = (250, 245, 62)
    m = (710, 245, 62)
    labels = [("acted_in {roles}", 172, -0.55), ("directed", 44, -0.28), ("produced", 15, 0.0),
              ("wrote", 10, 0.28), ("reviewed {summary, rating}", 9, 0.55)]
    import math
    for i, (name, n, _) in enumerate(labels):
        off = (i - 2) * 0.42                    # spread the five arcs around the straight line
        sx, sy = p[0] + p[2] * math.cos(off), p[1] + p[2] * math.sin(off)
        ex, ey = m[0] - (m[2] + 2) * math.cos(off), m[1] + (m[2] + 2) * math.sin(off)
        f.arrow(sx, sy, ex, ey, label=f"{name} · {n}", curve=(i - 2) * 70, size=13,
                label_dy=-2 if i < 2 else (12 if i > 2 else -4))
    f.node(*p, kind="user", label="")
    f.node(*m, kind="doc", label="")
    f.text(250, 240, "persons", size=18, anchor="middle", weight="bold")
    f.text(250, 262, "133 docs", size=13, anchor="middle", color=MUTED)
    f.text(710, 240, "movies", size=18, anchor="middle", weight="bold")
    f.text(710, 262, "38 docs", size=13, anchor="middle", color=MUTED)
    f.raw(f'<path d="M205,290 C150,380 330,380 290,292" fill="none" stroke="{INK}" stroke-width="2" '
          f'marker-end="url(#{f.marker(INK)})"/>')
    f.text(250, 372, "follows · 3", size=13, anchor="middle", color=MUTED, italic=True)
    f.code(40, 100, 220, ['{ "name": "Tom Hanks",', '  "born": 1956 }'], size=12, dark=False, hl=False, pad=9)
    f.code(700, 100, 240, ['{ "title": "Cast Away",', '  "released": 2000,', '  "tagline": "…" }'],
           size=12, dark=False, hl=False, pad=9)
    return f


@figure("ch04-text2aql-flow.svg")
def ch04_text2aql_flow():
    f = Fig(960, 470, "text2aql: the LLM writes the query, the database checks it",
            "a prompt with the schema in, an AQL query out - then EXPLAIN, run read-only, retry on error",
            desc="The question, the schema sampled from ArangoDB, terminology mappings, few-shot examples and "
                 "format instructions are assembled into a prompt. The LLM returns AQL. EXPLAIN checks it without "
                 "running it; a read-only user executes it with a time limit; if anything fails, the error message "
                 "goes back to the LLM for another attempt.")
    ins = [("question", "user"), ("schema", "db"), ("terminology", "gray"), ("few-shot examples", "gray"),
           ("format rules", "gray")]
    for i, (name, kind) in enumerate(ins):
        y = 110 + i * 54
        f.box(40, y, 170, 42, name, kind=kind, size=14)
        f.arrow(212, y + 21, 262, 230)
    f.code(264, 166, 160, ["PROMPT", "{schema}", "{terminology}", "{examples}", "{question}"], size=12,
           hl=False, pad=10)
    f.arrow(426, 230, 466, 230)
    f.llm(468, 196, 120, 68, "LLM", "")
    f.arrow(590, 230, 630, 230, label="AQL")
    f.box(632, 196, 128, 68, "EXPLAIN", "parse + plan, no run", kind="search", size=15)
    f.arrow(762, 230, 802, 230, label="ok")
    f.box(804, 186, 136, 88, "execute", "read-only user, max_runtime 10s", kind="db", size=15)
    f.arrow(872, 276, 872, 330)
    f.box(810, 332, 124, 44, "rows", kind="ok", size=15)
    f.poly([(696, 264), (696, 420), (528, 420), (528, 266)], color=RED, dashed=True,
           label="error message → fix it (max 3 tries)", label_at=1, label_dy=-8)
    f.poly([(872, 186), (872, 160), (528, 160), (528, 194)], color=RED, dashed=True)
    f.cylinder(46, 400, 150, 56, "ArangoDB", "", size=13)
    f.arrow(120, 398, 120, 368, label="sampled", label_dx=34)
    return f


@figure("ch04-prompt-anatomy.svg")
def ch04_prompt_anatomy():
    f = Fig(960, 520, "Anatomy of a text2aql prompt",
            "each section fixes a different way the LLM goes wrong",
            desc="The prompt has an instruction, the database schema, terminology mappings, few-shot examples, "
                 "format instructions and finally the user question; annotations explain what each part prevents.")
    parts = [
        ("Task", "Write one AQL query that retrieves the data to answer the question.", "doc",
         "sets the job"),
        ("Schema", "movies {title, released, tagline} · persons {name, born}\nacted_in: persons -> movies ...",
         "db", "stops invented collections & attributes"),
        ("Terminology", "actor / director / reviewer = persons + the edge type", "gray",
         "maps the user's words to the model"),
        ("Examples", "Question: ...  AQL: FOR p1 IN persons ...", "search",
         "teaches patterns it keeps getting wrong"),
        ("Format", "AQL only. No prose, no code fences.", "warn", "makes the output parseable"),
        ("Question", "Who directed the most movies?", "user", "goes last"),
    ]
    for i, (title, body, kind, note) in enumerate(parts):
        y = 100 + i * 68
        fill, stroke = KINDS[kind]
        f.raw(f'<rect x="60" y="{y}" width="560" height="58" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        f.text(76, y + 24, title.upper(), size=13, weight="bold", color=stroke)
        f.text(76, y + 44, body.split("\n")[0], size=13, font="mono")
        f.arrow(626, y + 29, 676, y + 29, color=RED, width=1.6)
        f.hand(684, y + 34, note, size=15)
    return f


# --------------------------------------------------------------------------
# Chapter 5
# --------------------------------------------------------------------------
@figure("ch05-agent-loop.svg")
def ch05_agent_loop():
    f = Fig(960, 520, "Agentic RAG: route, retrieve, criticize, answer",
            "the LLM picks the retriever; your code runs it; a critic checks the result (once)",
            desc="The question is first made specific by a query updater using earlier answers, then a router LLM "
                 "picks a tool and arguments; your code runs the tool's AQL against ArangoDB and appends the result "
                 "to the answers; a critic LLM lists missing information, which triggers one more round; finally an "
                 "LLM answers using only the collected answers.")
    f.person(50, 120, 0.85)
    f.box(84, 104, 160, 50, "user question", kind="user", size=14)
    f.arrow(246, 129, 288, 129)
    f.box(290, 100, 150, 58, "1 · query updater", "fills in earlier answers", kind="llm", size=14)
    f.arrow(442, 129, 486, 129)
    f.box(488, 100, 150, 58, "2 · router", "LLM + tool calling", kind="llm", size=14)
    tools = [("movie_info_by_title", "AQL template"), ("movies_info_by_actor", "AQL template"),
             ("text2aql", "LLM writes AQL (ch. 4)"), ("answer_given", "already answered")]
    for i, (t, sub) in enumerate(tools):
        y = 92 + i * 62
        f.box(690, y, 230, 50, t, sub, kind="search", size=13, sub_size=12)
        f.arrow(640, 129, 688, y + 25)
    f.cylinder(712, 352, 190, 66, "ArangoDB", "read-only", size=14)
    f.arrow(805, 340, 805, 350)
    f.poly([(690, 385), (520, 385), (520, 300)], label="results", label_at=0)
    f.box(410, 240, 220, 58, "answers so far", "\"For the question X we have Y\"", kind="doc", size=14,
          sub_size=12)
    f.arrow(408, 270, 340, 270)
    f.box(186, 240, 152, 58, "3 · critic", "anything missing?", kind="llm", size=14)
    f.poly([(262, 238), (262, 196), (365, 196), (365, 160)], color=RED, dashed=True,
           label="missing → new questions (one extra round)", label_at=1, label_dy=-8)
    f.arrow(262, 300, 262, 360, label="complete", label_dx=36)
    f.box(160, 362, 204, 58, "4 · final answer", "only from the answers", kind="ok", size=14)
    f.hand(40, 470, "The LLM never touches the database - it only says WHICH tool and WHAT arguments.",
           size=15)
    f.hand(40, 494, "Your code executes the tool. That's where safety & logging live.", size=15)
    return f


@figure("ch05-tool-call.svg")
def ch05_tool_call():
    f = Fig(960, 470, "Who does what in a tool call",
            "the model proposes, your application disposes",
            desc="Sequence: the app sends the question and tool descriptions to the LLM; the LLM replies with a "
                 "tool call naming a function and JSON arguments; the app runs the matching AQL query with bind "
                 "parameters; ArangoDB returns rows; the app sends the rows back as context; the LLM writes the "
                 "final answer.")
    lanes = [(150, "your app", "plain"), (480, "LLM", "llm"), (810, "ArangoDB", "db")]
    for x, name, kind in lanes:
        f.box(x - 80, 96, 160, 42, name, kind=kind, size=15)
        f.raw(f'<line x1="{x}" y1="140" x2="{x}" y2="450" stroke="#cfc6b4" stroke-width="2" stroke-dasharray="5 6"/>')
    msgs = [
        (150, 480, 175, "question + tool descriptions (JSON schema)"),
        (480, 150, 220, 'tool_calls: movie_info_by_title({"title": "The Matrix"})'),
        (150, 810, 265, "AQL template + @title bind parameter"),
        (810, 150, 310, "rows: title, cast, directors"),
        (150, 480, 355, "\"For the question … we have the answer …\""),
        (480, 150, 400, "final answer (grounded in the rows)"),
    ]
    for a, b, y, label in msgs:
        f.arrow(a, y, b, y, label=label, label_dy=-14, label_color=INK)
    f.note(540, 380, "your app: json.loads(arguments) → call the Python function", w=240, size=13, rot=1.5)
    return f


@figure("ch05-mcp.svg")
def ch05_mcp():
    f = Fig(960, 430, "Same tools, two ways to host them",
            "an in-process router (this chapter) vs. an MCP server any agent can use (bonus)",
            desc="Left: your Python process holds tool schemas, calls the LLM, runs the router loop and executes "
                 "AQL. Right: an MCP server exposes the same tools; an MCP host such as a desktop assistant or IDE "
                 "agent runs the reasoning loop and calls the tools over MCP; the server queries ArangoDB read-only.")
    f.raw('<rect x="30" y="92" width="430" height="310" rx="16" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
    f.raw('<rect x="500" y="92" width="430" height="310" rx="16" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
    f.text(245, 122, "In-process (ch05_agentic_rag.py)", size=16, weight="bold", anchor="middle")
    f.text(715, 122, "MCP server (ch05_mcp_server.py)", size=16, weight="bold", anchor="middle")
    f.box(60, 150, 370, 110, "your Python app", "router loop · query updater · critic · tool functions",
          kind="plain", size=15)
    f.llm(70, 290, 120, 56, "LLM", "")
    f.arrow(130, 288, 130, 262, both=True, label="chat API", label_dx=44)
    f.cylinder(280, 284, 140, 70, "ArangoDB", "", size=14)
    f.arrow(350, 262, 350, 282, both=True)
    f.box(530, 150, 180, 70, "MCP host", "Claude, IDE agent, …", kind="llm", size=15)
    f.box(530, 280, 180, 90, "MCP server", "3 tools, typed params", kind="search", size=15)
    f.arrow(620, 222, 620, 278, both=True, label="MCP (stdio)", label_dx=52)
    f.cylinder(760, 286, 140, 70, "ArangoDB", "read-only", size=14)
    f.arrow(712, 322, 758, 322, both=True)
    f.note(740, 150, "The host runs the loop; your server just answers tool calls.", w=170, size=13, rot=2)
    return f


# --------------------------------------------------------------------------
# Chapter 6
# --------------------------------------------------------------------------
@figure("ch06-chunk-mixing.svg")
def ch06_chunk_mixing():
    f = Fig(960, 470, "Why chunks alone fail on contracts",
            "similar-sounding text from the wrong contract vs. narrowing down with the graph first",
            desc="Left: a vector search for ACME's payment terms returns payment clauses from three different "
                 "contracts, and the LLM blends them. Right: the graph first finds ACME's contract via has_party, "
                 "then ranks only that contract's chunks by similarity.")
    f.raw('<rect x="30" y="92" width="430" height="350" rx="16" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
    f.raw('<rect x="500" y="92" width="430" height="350" rx="16" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
    f.text(245, 122, "Chunks only", size=17, weight="bold", anchor="middle")
    f.text(715, 122, "Graph first, then vectors", size=17, weight="bold", anchor="middle")
    f.box(60, 140, 370, 44, "payment terms of our license with ACME?", kind="user", size=14)
    f.arrow(245, 186, 245, 214, label="vector top-4", label_dx=50)
    colors = [("contract A (ACME)", "ok"), ("contract B (Globex)", "warn"), ("contract C (Initech)", "doc"),
              ("contract A (ACME)", "ok")]
    for i, (lab, kind) in enumerate(colors):
        f.box(70, 218 + i * 42, 350, 34, f"\"...payment within 30 days...\"  {lab}", kind=kind, size=12,
              bold=False)
    f.arrow(245, 388, 245, 404)
    f.box(110, 404, 270, 30, "LLM blends 3 contracts ✕", kind="warn", size=13)
    f.box(530, 140, 370, 44, "payment terms of our license with ACME?", kind="user", size=14)
    f.node(560, 240, 22, "", kind="user")
    f.text(560, 280, "organizations", size=12, anchor="middle", color=MUTED)
    f.text(560, 296, "ACME", size=13, anchor="middle", weight="bold")
    f.node(700, 240, 22, "", kind="db")
    f.text(700, 280, "contracts/A", size=13, anchor="middle", weight="bold")
    f.arrow(584, 240, 676, 240, label="has_party", label_dy=-12)
    for i in range(3):
        y = 196 + i * 44
        f.box(780, y, 120, 34, f"clause {i + 1}", kind="ok", size=13)
        f.arrow(722, 240, 778, y + 17)
    f.text(840, 340, "has_chunk", size=12, anchor="middle", color=MUTED, italic=True)
    f.arrow(715, 352, 715, 376, label="rank by COSINE_SIMILARITY", label_dx=96)
    f.box(590, 380, 260, 44, "only ACME's clauses ✓", kind="ok", size=14)
    return f


@figure("ch06-extraction.svg")
def ch06_extraction():
    f = Fig(960, 420, "From contract text to graph",
            "Structured Outputs turn prose into JSON that matches your schema; AQL UPSERTs it into the graph",
            desc="A contract document is sent to an LLM together with a Pydantic schema; Structured Outputs "
                 "guarantees JSON matching the schema; one AQL query upserts the contract, organizations, locations "
                 "and the edges between them.")
    f.doc(46, 150, 80, 104, label="contract.txt", lines=8)
    f.arrow(132, 202, 184, 202)
    f.llm(186, 160, 150, 84, "LLM", "+ Pydantic schema")
    f.code(150, 268, 230, ["class Contract(BaseModel):", "  contract_type: Literal[...]",
                           "  parties: list[Organization]", "  end_date: Optional[str]"],
           size=11, dark=False, hl=False, pad=8)
    f.arrow(338, 202, 386, 202, label="JSON")
    f.code(388, 110, 270, ['{ "contract_type": "Licensing',
                           '    Agreement",', '  "parties": [', '    { "name": "Northwind…",',
                           '      "role": "licensor",', '      "location": {…} }, …],',
                           '  "effective_date": "2025-03-01",', '  "end_date": "2027-02-28" }'],
           size=11, dark=False, hl=False, pad=10)
    f.arrow(660, 202, 708, 202, label="UPSERT")
    f.cylinder(710, 150, 210, 104, "ArangoDB", "contracts · organizations · locations + edges", size=15)
    f.note(690, 290, "Optional fields + \"if stated\" descriptions = fewer invented values.", w=240,
           size=14, rot=2)
    return f


@figure("ch06-contract-model.svg")
def ch06_contract_model():
    f = Fig(960, 420, "The contract graph in ArangoDB",
            "keys and unique indexes do the job of Neo4j's uniqueness constraints",
            desc="organizations link to contracts through has_party edges carrying a role, and to locations through "
                 "located_at edges; contracts link to contract_chunks through has_chunk. Contracts are keyed by a hash "
                 "of the document; organizations.name and locations.full_address have unique indexes.")
    f.box(40, 104, 230, 70, "locations", "unique index: full_address", kind="gray", size=16)
    f.box(40, 240, 230, 70, "organizations", "unique index: name", kind="user", size=16)
    f.box(390, 240, 240, 70, "contracts", "_key = hash(document text)", kind="db", size=16)
    f.box(730, 240, 200, 70, "contract_chunks", "one clause per chunk", kind="doc", size=16)
    f.arrow(155, 238, 155, 176, label="located_at", label_dx=48)
    f.arrow(272, 275, 388, 275, label="has_party {role}", label_dy=-14)
    f.arrow(632, 275, 728, 275, label="has_chunk", label_dy=-14)
    f.code(390, 326, 240, ["contract_type, effective_date,", "end_date, term, contract_scope,",
                           "total_amount, governing_law"], size=11, dark=False, hl=False, pad=8)
    f.code(730, 326, 200, ["text, embedding"], size=11, dark=False, hl=False, pad=8)
    f.note(40, 334, "re-import the same contract → same _key → updated, not duplicated", w=280, size=13,
           rot=-1.5)
    f.note(560, 120, "Neo4j: CREATE CONSTRAINT … IS UNIQUE.  ArangoDB: _key, or a unique persistent index.",
           w=300, size=13, rot=1.5)
    return f


@figure("ch06-entity-resolution.svg")
def ch06_entity_resolution():
    f = Fig(960, 400, "Entity resolution: three names, one company",
            "find candidates, pick a survivor, re-point the edges, remove the duplicates",
            desc="Three organization documents with name variants normalize to the same canonical string; the "
                 "survivor keeps its key, all has_party and located_at edges of the duplicates are updated to point at "
                 "it, and the duplicates are removed.")
    names = ["UTI Asset Management Company", "UTI Asset Management Company Limited",
             "UTI Asset Management Company Ltd"]
    for i, n in enumerate(names):
        y = 110 + i * 70
        f.box(40, y, 300, 50, n, kind="user", size=13)
        f.arrow(342, y + 25, 402, 195)
    f.box(404, 160, 200, 70, "normalize", "lower · strip legal suffixes · trim", kind="search", size=15)
    f.arrow(606, 195, 650, 195)
    f.box(652, 168, 260, 54, "\"uti asset management\"", kind="ok", size=15)
    f.code(40, 330, 560, ['UPDATE edge WITH { _from: survivor } IN has_party   // _from is mutable',
                          'REMOVE duplicate IN organizations'], size=12, hl=True, pad=10)
    f.note(652, 250, "Domain rules beat generic ones: 'Ltd' = 'Limited' is safe; 'Apple' vs 'Apple Records' is not.",
           w=270, size=13, rot=2)
    return f


# --------------------------------------------------------------------------
# Chapter 7
# --------------------------------------------------------------------------
@figure("ch07-pipeline.svg")
def ch07_pipeline():
    f = Fig(960, 500, "Microsoft-style GraphRAG, end to end",
            "indexing builds layers of LLM-written summaries; querying reads them back",
            desc="Indexing: text chunks, LLM extraction of entities and relationships with descriptions, LLM "
                 "summarization of duplicate descriptions, community detection, and an LLM-written report per "
                 "community. Querying: global search map-reduces over community reports; local search starts from the "
                 "entities most similar to the question and expands to related chunks, relationships and reports.")
    f.text(40, 112, "INDEXING  (expensive, once)", size=14, weight="bold", color=KINDS["db"][1])
    steps = [("chunks", "~1,000 chars", "doc"), ("extract", "entities + relations\nwith descriptions", "llm"),
             ("summarize", "merge duplicate\ndescriptions", "llm"), ("communities", "Louvain / Leiden", "search"),
             ("reports", "title, summary,\nrating, findings", "llm")]
    for i, (t, sub, kind) in enumerate(steps):
        x = 40 + i * 182
        f.box(x, 128, 160, 84, t, sub, kind=kind, size=15, sub_size=12)
        if i:
            f.arrow(x - 20, 170, x - 2, 170)
    f.cylinder(330, 250, 300, 80, "ArangoDB", "chunks · entities · communities + 4 edge collections", size=15)
    for x in (120, 302, 484, 666, 848):
        f.arrow(x, 214, 480 + (x - 484) * 0.35, 248, color="#b9b2a2", width=1.5)
    f.text(40, 372, "QUERYING  (every question)", size=14, weight="bold", color=KINDS["user"][1])
    f.box(40, 388, 430, 84, "Global search", "map-reduce over community reports - \"What is this story about?\"",
          kind="search", size=15, sub_size=12)
    f.box(490, 388, 430, 84, "Local search", "vector-find entities, expand to chunks, relationships, "
          "reports - \"Who is Ulysses?\"", kind="search", size=15, sub_size=12)
    f.arrow(380, 332, 255, 386)
    f.arrow(580, 332, 705, 386)
    return f


@figure("ch07-graph-model.svg")
def ch07_graph_model():
    f = Fig(960, 440, "The GraphRAG index in ArangoDB",
            "three document collections, four edge collections - and two levels of detail",
            desc="chunks link to entities via has_entity; entities link to each other via related (one raw edge per "
                 "extracted relationship, many per pair) and summarized (one edge per pair with an LLM summary); entities "
                 "link to communities via in_community. Entity documents keep the raw descriptions list and a summary.")
    f.box(40, 120, 170, 64, "chunks", "book, chunk, text", kind="doc", size=16)
    f.box(390, 120, 190, 64, "entities", "name, type", kind="user", size=16)
    f.box(760, 120, 170, 64, "communities", "title, report, rating", kind="search", size=16)
    f.arrow(212, 152, 388, 152, label="has_entity", label_dy=-14)
    f.arrow(582, 152, 758, 152, label="in_community", label_dy=-14)
    f.raw(f'<path d="M430,186 C380,290 590,290 540,186" fill="none" stroke="{INK}" stroke-width="2" '
          f'marker-end="url(#{f.marker(INK)})"/>')
    f.text(485, 236, "related (raw)", size=13, anchor="middle", color=MUTED, italic=True)
    f.raw(f'<path d="M410,186 C330,350 640,350 560,186" fill="none" stroke="{KINDS["db"][1]}" stroke-width="3" '
          f'marker-end="url(#{f.marker(KINDS["db"][1])})"/>')
    f.text(485, 332, "summarized (1 per pair)", size=13, anchor="middle", color=KINDS["db"][1], weight="bold")
    f.code(40, 330, 330, ['// entities/ORESTES', '"descriptions": [ "…son of Agamemnon…",',
                          '   "…praised for avenging…", … ],', '"summary": "Orestes is the son of …"'],
           size=11, dark=False, hl=False, pad=9)
    f.code(620, 330, 310, ['// TELEMACHUS - MINERVA', '14 x related  →  1 x summarized',
                           '{ summary, weight, count, rank }'], size=11, dark=False, hl=False, pad=9)
    return f


@figure("ch07-communities.svg")
def ch07_communities():
    f = Fig(960, 470, "Communities: groups of densely connected entities",
            "each community gets an LLM-written report that later answers global questions",
            desc="An entity graph is partitioned into communities, drawn as colored groups. One community around "
                 "Minerva and Telemachus has a report card with a title, rating, summary and findings.")
    import math
    clusters = [
        ((200, 230), ["MINERVA", "TELEMACHUS", "PENELOPE", "SUITORS", "ITHACA"], "search"),
        ((440, 330), ["AEGISTHUS", "ORESTES", "AGAMEMNON", "MERCURY"], "warn"),
        ((450, 178), ["JOVE", "NEPTUNE", "POLYPHEMUS"], "db"),
    ]
    pos = {}
    for (cx, cy), names, kind in clusters:
        fill, stroke = KINDS[kind]
        f.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="{70 + 14 * len(names)}" ry="{58 + 8 * len(names)}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-dasharray="6 5" opacity="0.8"/>')
        for i, n in enumerate(names):
            a = 2 * math.pi * i / len(names) - math.pi / 2
            pos[n] = (cx + (34 + 10 * len(names)) * math.cos(a), cy + (26 + 7 * len(names)) * math.sin(a), 9)
    links = [("MINERVA", "TELEMACHUS"), ("TELEMACHUS", "PENELOPE"), ("PENELOPE", "SUITORS"),
             ("SUITORS", "TELEMACHUS"), ("ITHACA", "TELEMACHUS"), ("MINERVA", "ITHACA"),
             ("AEGISTHUS", "ORESTES"), ("ORESTES", "AGAMEMNON"), ("AGAMEMNON", "AEGISTHUS"),
             ("MERCURY", "AEGISTHUS"), ("JOVE", "NEPTUNE"), ("NEPTUNE", "POLYPHEMUS"), ("JOVE", "MINERVA"),
             ("JOVE", "MERCURY")]
    for a, b in links:
        (x1, y1, _), (x2, y2, _) = pos[a], pos[b]
        f.raw(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" stroke-width="1.6" opacity="0.7"/>')
    for n, (x, y, r) in pos.items():
        f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="1.8"/>')
        f.text(x, y - 13, n, size=11, anchor="middle", weight="bold", halo=True)
    f.raw(f'<rect x="620" y="96" width="310" height="350" rx="12" fill="#ffffff" stroke="{KINDS["search"][1]}" stroke-width="2"/>')
    f.text(636, 124, "communities/c0", size=12, color=MUTED, font="mono")
    f.text(636, 150, "Minerva, Telemachus and", size=16, weight="bold")
    f.text(636, 170, "the Ithacan household", size=16, weight="bold")
    f.pill(636, 202, "rating 8.5 / 10", kind="ok", size=12)
    f.text(636, 236, "Summary", size=13, weight="bold", color=KINDS["search"][1])
    f.text(636, 256, "Minerva guides Telemachus as he looks for\nhis father and confronts the suitors…",
           size=12, color=MUTED, lh=16)
    f.text(636, 304, "Findings", size=13, weight="bold", color=KINDS["search"][1])
    for i, s in enumerate(["Minerva acts as divine mentor", "The suitors threaten the household",
                           "Telemachus grows into his role", "…5-10 findings in total"]):
        f.text(646, 326 + i * 22, "• " + s, size=12)
    f.arrow(300, 170, 616, 200, color=KINDS["search"][1], curve=-30)
    return f


@figure("ch07-global-search.svg")
def ch07_global_search():
    f = Fig(960, 460, "Global search = map-reduce over community reports",
            "for broad questions no single chunk can answer",
            desc="Community reports with a rating above a threshold are packed into batches. MAP: each batch and the "
                 "question go to an LLM that returns key points with importance scores and report references. REDUCE: "
                 "points with score above zero are sorted by importance and a final LLM call writes the answer, keeping "
                 "the references.")
    f.box(40, 110, 200, 54, "What is this", "story about?", kind="user", size=14, sub_size=14)
    f.cylinder(40, 200, 200, 90, "reports", "rating ≥ 5, packed into token-sized batches", size=15, kind="search")
    f.arrow(140, 166, 140, 198)
    for i in range(3):
        y = 104 + i * 104
        f.box(300, y, 140, 50, f"batch {i + 1}", "3-4 reports", kind="search", size=14, sub_size=12)
        f.arrow(242, 245, 298, y + 25)
        f.llm(480, y - 4, 110, 58, "MAP", "")
        f.arrow(442, y + 25, 478, y + 25)
        f.code(630, y - 6, 300, [f'{{"description": "… [Data: Reports ({i * 3 + 1})]",',
                                 f'  "score": {[85, 60, 0][i]} }}'], size=11, dark=False, hl=False, pad=8)
        f.arrow(592, y + 25, 628, y + 25)
    f.raw(f'<line x1="640" y1="{104 + 2 * 104 + 30}" x2="920" y2="{104 + 2 * 104 + 30}" stroke="{RED}" stroke-width="2"/>')
    f.hand(800, 372, "score 0 → dropped", size=14)
    f.box(500, 392, 200, 54, "sort by score", "keep the best points", kind="gray", size=14, sub_size=12)
    f.arrow(780, 380, 702, 410)
    f.arrow(498, 419, 452, 419)
    f.llm(330, 390, 120, 58, "REDUCE", "")
    f.arrow(328, 419, 262, 419)
    f.box(40, 392, 220, 54, "answer + [Data: Reports (…)]", kind="ok", size=13)
    return f


@figure("ch07-local-search.svg")
def ch07_local_search():
    f = Fig(960, 480, "Local search = start at the right entities, then expand",
            "one AQL query gathers four kinds of context, each ranked and capped",
            desc="The question is embedded and the vector index returns the top-k entities. From them, one AQL query "
                 "collects the chunks that mention them (ranked by number of mentions), their community reports "
                 "(ranked by matched entities and rating), the summarized relationships among them (ranked by "
                 "rank and weight), and the entity summaries; the tables go into the prompt.")
    f.box(40, 110, 170, 54, "Who is", "Ulysses?", kind="user", size=14, sub_size=14)
    f.arrow(125, 166, 125, 206, label="embed", label_dx=30)
    f.box(40, 208, 170, 70, "vector index", "APPROX_NEAR_COSINE on entities", kind="search", size=14,
          sub_size=12)
    f.arrow(212, 243, 270, 243)
    for x, y in [(310, 200), (350, 250), (300, 296)]:
        f.raw(f'<circle cx="{x}" cy="{y}" r="16" fill="{KINDS["user"][0]}" stroke="{KINDS["user"][1]}" stroke-width="2"/>')
    f.text(325, 340, "top-k entities", size=13, anchor="middle", color=MUTED)
    outs = [("Sources", "chunks that mention them · by # mentions", "doc"),
            ("Reports", "their communities · by matches, rating", "search"),
            ("Relationships", "summarized edges among them · by rank", "db"),
            ("Entities", "their summaries · all k", "user")]
    for i, (t, sub, kind) in enumerate(outs):
        y = 96 + i * 84
        f.box(430, y, 270, 66, t, sub, kind=kind, size=15, sub_size=12)
        f.arrow(370, 248, 428, y + 33, color="#8b8578", width=1.6)
        f.arrow(702, y + 33, 772, 262, color="#8b8578", width=1.6)
    f.llm(774, 230, 150, 64, "LLM", "context tables")
    f.arrow(849, 228, 849, 166, color=KINDS["ok"][1])
    f.box(774, 116, 150, 48, "answer", "with [Data: …] refs", kind="ok", size=14, sub_size=11)
    f.text(565, 446, "each list is capped: top_chunks, top_communities, top_inside_rels", size=12,
           anchor="middle", color=MUTED, italic=True)
    f.hand(40, 470, "the graph supplies the CONTEXT around the entities, not just the most similar text",
           size=15)
    return f


# --------------------------------------------------------------------------
# Chapter 8
# --------------------------------------------------------------------------
@figure("ch08-eval-points.svg")
def ch08_eval_points():
    f = Fig(960, 430, "Where to measure a RAG pipeline",
            "four checkpoints - test them separately and end to end",
            desc="The pipeline goes from user question to tool selection, to retrieved context, to the generated "
                 "answer. Evaluation checkpoints: was the right tool chosen, is the retrieved context relevant and "
                 "complete, is the answer faithful to the context and correct versus the ground truth, and how does "
                 "the whole pipeline perform end to end including latency.")
    f.person(60, 200, 0.9)
    f.box(96, 186, 130, 54, "question", kind="user", size=15)
    f.arrow(228, 213, 278, 213)
    f.llm(280, 180, 130, 66, "router", "picks a tool")
    f.arrow(412, 213, 462, 213)
    f.box(464, 180, 150, 66, "retriever", "AQL / vectors", kind="search", size=15)
    f.arrow(616, 213, 666, 213)
    f.box(668, 180, 120, 66, "context", kind="doc", size=15)
    f.arrow(790, 213, 832, 213)
    f.llm(834, 180, 100, 66, "LLM", "answer")
    checks = [(345, "1 · right tool?", "tool-selection tests"), (541, "2 · context recall", "did we fetch it all?"),
              (728, "3 · faithfulness", "answer ⊂ context?"), (884, "4 · correctness", "answer = truth?")]
    for x, t, sub in checks:
        f.raw(f'<line x1="{x}" y1="{256}" x2="{x}" y2="{300}" stroke="{RED}" stroke-width="2" stroke-dasharray="4 4"/>')
        f.text(x, 322, t, size=14, anchor="middle", weight="bold", color=RED)
        f.text(x, 342, sub, size=12, anchor="middle", color=MUTED)
    f.raw(f'<path d="M96,140 Q520,70 934,140" fill="none" stroke="{RED}" stroke-width="2" stroke-dasharray="6 5"/>')
    f.hand(430, 118, "end to end: answer quality + latency", size=15)
    f.hand(60, 400, "Test generation separately: does the LLM answer correctly when GIVEN the right context?",
           size=14, color=MUTED)
    return f


@figure("ch08-ground-truth.svg")
def ch08_ground_truth():
    f = Fig(960, 330, "A benchmark row whose ground truth is a query",
            "the expected answer is computed fresh, so the test stays valid when the data changes",
            desc="Each benchmark row has a question and an AQL query. The query runs against today's database to "
                 "produce the ground truth; the agent answers the same question; the judge compares the two. Static "
                 "answers are AQL RETURN of a string.")
    f.code(40, 100, 420, ["question;aql", "How many movies did Tom Hanks appear in?;",
                          "  FOR p IN persons FILTER p.name == \"Tom Hanks\"",
                          "    RETURN { movies: LENGTH(FOR m IN 1..1", "      OUTBOUND p acted_in RETURN 1) }",
                          "Hello;RETURN \"a greeting and a reminder…\""],
           size=12, title="data/benchmark.csv", pad=12)
    f.arrow(466, 150, 540, 150, label="run AQL", label_dy=-12)
    f.box(542, 120, 170, 60, "ground truth", "[{\"movies\": 12}]", kind="ok", size=14)
    f.arrow(466, 250, 540, 250, label="ask agent", label_dy=-12)
    f.box(542, 220, 170, 60, "agent answer", "\"Tom Hanks appeared in 12…\"", kind="user", size=14, sub_size=11)
    f.arrow(714, 150, 790, 196)
    f.arrow(714, 250, 790, 210)
    f.box(792, 172, 140, 60, "LLM judge", "3 metrics", kind="llm", size=14)
    return f


@figure("ch08-metrics.svg")
def ch08_metrics():
    f = Fig(960, 470, "Three metrics, one trick: break text into statements",
            "then check each statement against something",
            desc="Context recall: statements of the ground truth checked against the retrieved context. Faithfulness: "
                 "statements of the answer checked against the retrieved context. Answer correctness: answer "
                 "statements compared with ground-truth statements as true positives, false positives and false "
                 "negatives, combined into an F1 score.")
    cols = [(40, "Context recall", "ground-truth statements", "found in the context?",
             [("Tom Hanks acted in 12 movies", True), ("one was Cast Away", True), ("one was Apollo 13", False)],
             "2 / 3 = 0.67", "retriever missed something"),
            (350, "Faithfulness", "answer statements", "supported by the context?",
             [("Hanks made 12 movies", True), ("including Cast Away", True), ("he won two Oscars", False)],
             "2 / 3 = 0.67", "the LLM added a claim"),
            (660, "Answer correctness", "answer vs ground truth", "TP · FP · FN",
             [("12 movies  → TP", True), ("two Oscars → FP", False), ("Apollo 13 missing → FN", False)],
             "TP/(TP+½(FP+FN)) = 0.5", "right, wrong and missing")]
    for x, title, sub, q, rows, score, note in cols:
        f.raw(f'<rect x="{x}" y="92" width="270" height="350" rx="14" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
        f.text(x + 135, 122, title, size=17, weight="bold", anchor="middle")
        f.text(x + 135, 144, sub, size=12, anchor="middle", color=MUTED)
        f.text(x + 135, 176, q, size=13, anchor="middle", weight="bold", color=KINDS["search"][1])
        for i, (s, ok) in enumerate(rows):
            y = 196 + i * 50
            kind = "ok" if ok else "warn"
            f.box(x + 16, y, 238, 38, s, kind=kind, size=12, bold=False)
        f.text(x + 135, 372, score, size=16, anchor="middle", weight="bold")
        f.hand(x + 135, 402, note, size=14, anchor="middle")
    return f


# --------------------------------------------------------------------------
# Chapter 9
# --------------------------------------------------------------------------
@figure("ch09-which-retriever.svg")
def ch09_which_retriever():
    f = Fig(960, 520, "Which retriever for which question?",
            "start from what the answer needs - not from the tool you like",
            desc="A decision guide: fuzzy facts in text use vector or hybrid search; exact terms use BM25 hybrid; "
                 "answers needing more context than a chunk use the parent document retriever; counting, filtering, "
                 "ranking and multi-hop questions use AQL templates or text2aql; everything about one entity uses "
                 "local search; themes across the corpus use global search; mixed questions go through an agentic router.")
    f.box(30, 220, 210, 90, "What does the\nanswer need?", kind="user", size=16)
    rows = [
        ("a fact stated in some text", "vector / hybrid search", "ch. 2", "doc"),
        ("exact names, codes, rare words", "hybrid: + BM25 view", "ch. 2", "doc"),
        ("more context than one chunk", "parent document retriever", "ch. 3", "doc"),
        ("count · filter · rank · multi-hop", "AQL template or text2aql", "ch. 4-5", "search"),
        ("everything about one entity", "local search", "ch. 7", "db"),
        ("themes across the whole corpus", "global search", "ch. 7", "db"),
        ("a mix of the above", "agentic router + tools", "ch. 5", "llm"),
    ]
    for i, (need, tool, ch, kind) in enumerate(rows):
        y = 96 + i * 58
        f.text(300, y + 28, need, size=14, color=INK)
        f.arrow(242, 265, 292, y + 23, color="#b9b2a2", width=1.4)
        f.arrow(560, y + 23, 600, y + 23, color=INK, width=1.6)
        f.box(602, y, 250, 44, tool, kind=kind, size=14)
        f.text(868, y + 28, ch, size=13, color=MUTED, italic=True)
    return f


@figure("ch09-architecture.svg")
def ch09_architecture():
    f = Fig(960, 530, "A reference architecture for GraphRAG on ArangoDB",
            "everything in this guide, in one picture",
            desc="Sources flow through ingestion (chunk, embed, extract with an LLM, resolve entities, summarize, detect "
                 "communities) into ArangoDB, which stores documents, graph edges, a vector index and an ArangoSearch "
                 "view. Retrievers (vector and hybrid, parent document, AQL templates, text2aql, local and global "
                 "search) are chosen by an agent with a router and critic; the LLM answers; an evaluation loop with "
                 "AQL ground truth feeds improvements back. Tools can also be exposed over MCP.")
    f.box(30, 100, 150, 120, "Sources", "PDFs, contracts, books, wikis, tables", kind="doc", size=15)
    f.arrow(182, 160, 220, 160)
    f.raw('<rect x="222" y="96" width="250" height="128" rx="14" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
    f.text(347, 120, "Ingestion", size=15, weight="bold", anchor="middle")
    for i, s in enumerate(["chunk + embed  (ch. 2-3)", "extract with LLM  (ch. 6-7)", "resolve entities  (ch. 6)",
                           "summarize + communities  (ch. 7)"]):
        f.text(240, 146 + i * 21, "• " + s, size=13)
    f.arrow(474, 160, 512, 160)
    f.cylinder(514, 92, 410, 140, "ArangoDB 3.12", "", size=17)
    for i, (t, kind) in enumerate([("documents", "doc"), ("graph edges", "db"), ("vector index", "search"),
                                   ("search view", "gray")]):
        f.pill(538 + i * 98, 196, t, kind=kind, size=12)
    f.arrow(720, 234, 720, 270, both=True, label="AQL", label_dx=24)
    f.raw('<rect x="420" y="272" width="510" height="96" rx="14" fill="#ffffff" stroke="#e3d9c6" stroke-width="2"/>')
    f.text(675, 294, "Retrievers", size=15, weight="bold", anchor="middle")
    for i, t in enumerate(["vector/hybrid", "parent docs", "AQL templates", "text2aql", "local", "global"]):
        f.pill(436 + (i % 3) * 164, 322 + (i // 3) * 30, t, kind="search", size=12)
    f.arrow(418, 320, 352, 320, both=True)
    f.box(170, 280, 180, 84, "Agent", "router · query updater · critic", kind="llm", size=15)
    f.arrow(260, 366, 260, 404)
    f.box(170, 406, 180, 54, "LLM answer", "grounded + cited", kind="ok", size=14)
    f.person(76, 300, 0.9)
    f.arrow(100, 322, 168, 322, both=True)
    f.box(420, 404, 510, 64, "Evaluation loop", "benchmark with AQL ground truth · recall · faithfulness · "
          "correctness · latency", kind="user", size=15)
    f.arrow(860, 402, 860, 372, color=RED, dashed=True, label="improve", label_dx=34)
    f.hand(340, 500, "every failure becomes a test, a few-shot example or a new tool", size=15)
    f.pill(780, 268, "also via MCP", kind="llm", size=12)
    return f


# --------------------------------------------------------------------------
def main(names=None):
    for name, fn in FIGURES.items():
        if names and name not in names:
            continue
        fig = fn()
        fig.save(os.path.join(OUT, name))
        print("wrote", name)


if __name__ == "__main__":
    main(sys.argv[1:])
