"""Readable numeric-tree rules, diagrams and aggregate audit exports."""

from __future__ import annotations

import gzip
import io
import json
import zipfile

import pandas as pd

LABELS = {
    "horas_ciclo_anterior": "Horas no ciclo anterior",
    "horas_2_ciclos_atras": "Horas há dois ciclos",
    "media_3_ciclos": "Média dos três ciclos anteriores",
    "media_6_ciclos": "Média dos seis ciclos anteriores",
    "horas_folga_anterior": "Extras em folgas no ciclo anterior",
    "horas_trabalho_anterior": "Extras em dias de trabalho no ciclo anterior",
    "media_equipe_anterior": "Média anterior da mesma unidade e função",
    "tempo_casa_meses": "Tempo de casa em meses",
    "dias_uteis_ciclo": "Dias de segunda a sexta no ciclo",
    "mes_sin": "Época do ano (seno)",
    "mes_cos": "Época do ano (cosseno)",
    **{f"unidade_{i}": f"É da Unidade {chr(65 + i)} (1=sim)" for i in range(3)},
    **{
        f"funcao_{i}": f"É de {role} (1=sim)"
        for i, role in enumerate(("Operação", "Manutenção", "Logística"))
    },
}


def leaf_catalog(nodes: pd.DataFrame) -> pd.DataFrame:
    paths = []
    for tree, group in nodes.groupby("Tree", sort=True):
        rows = group.set_index("Node")

        def walk(node, conditions):
            row = rows.loc[node]
            if row.Feature == "Leaf":
                paths.append(
                    {
                        "arvore": int(tree) + 1,
                        "no_folha": int(node),
                        "condicoes": " → ".join(conditions) or "Folha raiz",
                        "correcao_por_pessoa_h": float(row.Gain),
                    }
                )
                return
            name = LABELS.get(str(row.Feature), str(row.Feature))
            for child, sign in ((row.Yes, "<"), (row.No, "≥")):
                condition = f"{name} {sign} {float(row.Split):.8g}"
                if child == row.Missing:
                    condition += " (ou ausente)"
                walk(int(str(child).rsplit("-", 1)[-1]), [*conditions, condition])

        walk(0, [])
    return pd.DataFrame(paths)


def tree_diagram(nodes: pd.DataFrame, tree: int) -> str:
    lines = [
        "digraph Tree {",
        "rankdir=TB;",
        'node [shape=box, style="rounded,filled", fontname="Arial", fillcolor="#eef4f7"];',
    ]
    for row in nodes.loc[nodes.Tree.eq(tree - 1)].itertuples():
        if row.Feature == "Leaf":
            label = f"Folha {row.Node}\nAjuste: {row.Gain:+.4f} h/pessoa"
            lines.append(f'{row.Node} [label={json.dumps(label)}, fillcolor="#d9eee7"];')
        else:
            label = f"{LABELS.get(row.Feature, row.Feature)}\nMenor que {row.Split:.8g}?"
            lines.append(f"{row.Node} [label={json.dumps(label)}];")
            for child, answer in ((row.Yes, "Sim"), (row.No, "Não")):
                suffix = " / ausente" if child == row.Missing else ""
                node = int(str(child).rsplit("-", 1)[-1])
                lines.append(f"{row.Node} -> {node} [label={json.dumps(answer + suffix)}];")
    return "\n".join([*lines, "}"])


def tree_dump(model) -> bytes:
    return gzip.compress(
        json.dumps(
            {
                "data_origin": "synthetic",
                "tree_count": model.num_boosted_rounds(),
                "trees": [json.loads(item) for item in model.get_dump(dump_format="json")],
            },
            ensure_ascii=False,
        ).encode("utf-8")
    )


def audit_package(trace: dict, model, cycle: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key in ("trees", "routes", "contributions", "factors"):
            archive.writestr(f"{cycle}_{key}.csv", trace[key].to_csv(index=False))
        archive.writestr("arvores_sinteticas.json.gz", tree_dump(model))
        archive.writestr(
            "reconciliacao.json",
            json.dumps(
                {
                    "data_origin": "synthetic",
                    "cycle": cycle,
                    **{
                        key: trace[key]
                        for key in (
                            "base_score",
                            "factor_sum",
                            "base_hours",
                            "tree_hours",
                            "total_hours",
                            "people",
                        )
                    },
                },
                indent=2,
            ),
        )
        archive.writestr(
            "LEIA-ME.txt",
            "Demonstração integralmente sintética. Os efeitos "
            "incluem calibração por função e zeragem das previsões negativas. "
            "A base mais os efeitos das árvores reconcilia com o total. "
            "Não contém identificadores nem dados do projeto privado.",
        )
    return buffer.getvalue()
