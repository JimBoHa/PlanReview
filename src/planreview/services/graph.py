from __future__ import annotations

from dataclasses import dataclass, field

from planreview.services.document_analysis import PageSemantics
from planreview.services.semantic_model import get_local_semantic_encoder
from planreview.services.spec_parser import SpecSectionSemantics


@dataclass
class GraphNode:
    id: str
    kind: str
    label: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: str
    score: float = 1.0


@dataclass
class ProjectGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def outgoing(self, source_id: str, relation: str | None = None) -> list[GraphEdge]:
        return [
            edge
            for edge in self.edges
            if edge.source_id == source_id and (relation is None or edge.relation == relation)
        ]


def build_project_graph(
    drawing_pages: list[tuple[str, int, PageSemantics, str]],
    spec_sections: list[SpecSectionSemantics],
) -> ProjectGraph:
    graph = ProjectGraph()
    for document_id, page_number, semantics, _text in drawing_pages:
        page_id = f"page:{document_id}:{page_number}"
        graph.add_node(
            GraphNode(
                id=page_id,
                kind="drawing-page",
                label=semantics.sheet_number or f"page {page_number}",
                metadata={
                    "discipline": semantics.discipline,
                    "page_class": semantics.page_class,
                },
            )
        )
        if semantics.sheet_number:
            sheet_id = f"sheet:{semantics.sheet_number}"
            graph.add_node(
                GraphNode(
                    id=sheet_id,
                    kind="sheet",
                    label=semantics.sheet_number,
                    metadata={"discipline": semantics.discipline},
                )
            )
            graph.add_edge(GraphEdge(source_id=page_id, target_id=sheet_id, relation="sheet-id"))
        for reference in semantics.detail_references:
            target_sheet = reference.split("/", 1)[1]
            graph.add_edge(
                GraphEdge(
                    source_id=page_id,
                    target_id=f"sheet:{target_sheet}",
                    relation="detail-callout",
                )
            )

    section_text_map: dict[str, str] = {}
    for section in spec_sections:
        node_id = f"spec:{section.section_number}"
        section_text_map[node_id] = (
            f"{section.section_number} {section.title}\n{section.text[:2500]}"
        )
        graph.add_node(
            GraphNode(
                id=node_id,
                kind="spec-section",
                label=f"{section.section_number} {section.title}".strip(),
                metadata={"section_number": section.section_number},
            )
        )

    encoder = get_local_semantic_encoder()
    for document_id, page_number, semantics, text in drawing_pages:
        page_id = f"page:{document_id}:{page_number}"
        for section in semantics.spec_section_references:
            graph.add_edge(
                GraphEdge(
                    source_id=page_id,
                    target_id=f"spec:{section}",
                    relation="spec-reference",
                )
            )
        if not section_text_map:
            continue
        ranked = encoder.rank(text[:2500], section_text_map, threshold=0.32)
        for match in ranked[:3]:
            graph.add_edge(
                GraphEdge(
                    source_id=page_id,
                    target_id=match.target_id,
                    relation="semantic-spec-link",
                    score=match.score,
                )
            )

    return graph
