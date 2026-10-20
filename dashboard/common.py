"""Shared formatting, cached artifacts and charts."""

import json
import logging
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import xgboost as xgb

from demo_pipeline import audit_demo
from tree_audit import leaf_catalog

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
COLORS = ["#55718a", "#087f73", "#ca8751"]


def render_safely(renderer, *args):
    """Keep internal diagnostics in server logs, never in the public page."""
    try:
        renderer(*args)
    except Exception:
        logging.getLogger(__name__).exception("Falha ao renderizar o painel público")
        st.error(
            "Não foi possível concluir esta operação. Reinicie a aplicação e tente novamente. "
            "Se o problema persistir, consulte os logs locais ou abra uma issue sem incluir dados pessoais."
        )


def number(value, decimals=0):
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def version():
    return tuple(
        path.stat().st_mtime_ns
        for path in (
            *(
                ARTIFACTS / name
                for name in (
                    "metadata.json",
                    "demo_model.json",
                    "projection_features.csv",
                    "monthly.csv",
                    "forecast.csv",
                    "history.csv",
                )
            ),
            ROOT / "demo_pipeline.py",
            ROOT / "tree_audit.py",
        )
    )


@st.cache_data(show_spinner=False)
def load_artifacts(signature):
    meta = json.loads((ARTIFACTS / "metadata.json").read_text(encoding="utf-8"))
    if meta.get("data_origin") != "synthetic":
        raise ValueError("A versão pública aceita somente artefatos sintéticos.")
    tables = {
        name: pd.read_csv(ARTIFACTS / f"{name}.csv")
        for name in ("monthly", "forecast", "history", "projection_features")
    }
    return meta, tables


@st.cache_resource(show_spinner=False)
def load_model(signature):
    model = xgb.Booster()
    model.load_model(ARTIFACTS / "demo_model.json")
    model.set_param({"nthread": 2})
    return model


@st.cache_data(show_spinner=False, max_entries=12)
def load_audit(signature, cycle):
    meta, tables = load_artifacts(signature)
    frame = tables["projection_features"]
    frame = frame.loc[frame.ciclo.eq(cycle)].copy()
    if frame.empty:
        raise ValueError("Ciclo indisponível na projeção sintética.")
    return audit_demo(load_model(signature), frame, meta["calibration_factors"])


@st.cache_data(show_spinner=False, max_entries=2)
def load_catalog(signature):
    nodes = load_model(signature).trees_to_dataframe()
    catalog = nodes.groupby("Tree", as_index=False).agg(
        perguntas=("Feature", lambda values: int(values.ne("Leaf").sum())),
        folhas=("Feature", lambda values: int(values.eq("Leaf").sum())),
    )
    catalog["arvore"] = catalog.pop("Tree") + 1
    return catalog, leaf_catalog(nodes), nodes


def line_chart(frame, series):
    return (
        alt.Chart(frame)
        .mark_line(point=True, strokeWidth=2.6)
        .encode(
            x=alt.X("data:T", title=None, axis=alt.Axis(format="%b/%y", labelAngle=0)),
            y=alt.Y("horas:Q", title="Horas extras sintéticas", scale=alt.Scale(zero=True)),
            color=alt.Color(
                "serie:N",
                title=None,
                scale=alt.Scale(domain=series, range=COLORS),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("ciclo:N", title="Ciclo"),
                "serie:N",
                alt.Tooltip("horas:Q", title="Horas", format=",.1f"),
            ],
        )
        .properties(height=330)
        .interactive()
    )


def effect_chart(frame, label, count=18):
    selected = frame.assign(magnitude=frame.efeito_horas.abs()).nlargest(count, "magnitude")
    return (
        alt.Chart(selected)
        .mark_bar()
        .encode(
            x=alt.X("efeito_horas:Q", title="Efeito agregado após calibração (h)"),
            y=alt.Y(f"{label}:N", title=None, sort="-x", axis=alt.Axis(labelLimit=300)),
            color=alt.condition(
                alt.datum.efeito_horas >= 0, alt.value(COLORS[1]), alt.value(COLORS[2])
            ),
            tooltip=[f"{label}:N", alt.Tooltip("efeito_horas:Q", format="+.3f")],
        )
        .properties(height=max(260, len(selected) * 24))
    )


def csv_download(label, frame, filename, key=None):
    st.download_button(
        label,
        frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )
