"""Assemblage du graphe : nodes + edges. C'est ici, et seulement ici, qu'on lit le flux."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.config import Settings
from app.graph.nodes import Judge, Writer, make_nodes
from app.graph.routing import decide_after_human, route_from_decision
from app.graph.state import EmailState


def build_graph(judge: Judge, writer: Writer, settings: Settings,
                checkpointer: BaseCheckpointSaver | None = None):
    nodes = make_nodes(judge, writer, settings)
    g = StateGraph(EmailState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.add_edge(START, "analyze")
    # Edges conditionnels : la fonction renvoie le nom du node suivant.
    # La liste des destinations possibles sert aussi à dessiner le graphe.
    g.add_conditional_edges("analyze", route_from_decision, ["draft", "human_review", "finalize"])
    g.add_edge("draft", "verify")
    g.add_conditional_edges("verify", route_from_decision, ["draft", "human_review", "finalize"])
    g.add_conditional_edges("human_review", decide_after_human, ["draft", "finalize"])
    g.add_edge("finalize", END)

    # Le checkpointer sauvegarde l'état après chaque node : indispensable pour interrupt().
    return g.compile(checkpointer=checkpointer or InMemorySaver())
