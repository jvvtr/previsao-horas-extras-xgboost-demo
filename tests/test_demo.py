import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from streamlit.testing.v1 import AppTest

from demo_pipeline import FEATURES, _matrix, audit_demo, cycle_label, synthetic_panel
from tree_audit import audit_package, tree_diagram

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def test_generator_is_deterministic_and_uses_only_fictional_groups():
    first, future = synthetic_panel()
    again, _ = synthetic_panel()
    assert len(future) == 180
    assert set(future.unidade) == {"Unidade A", "Unidade B", "Unidade C"}
    assert set(future.funcao) == {"Operação", "Manutenção", "Logística"}
    assert first.horas.equals(again.horas)
    assert "cod_pessoa" not in first.columns


def test_public_artifacts_reconcile_with_the_synthetic_model():
    metadata = json.loads((ARTIFACTS / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["data_origin"] == "synthetic"
    future = pd.read_csv(ARTIFACTS / "future_features.csv")
    assert set(FEATURES).issubset(future.columns)
    assert "cod_pessoa" not in future.columns
    model = xgb.Booster()
    model.load_model(ARTIFACTS / "demo_model.json")
    trace = audit_demo(model, future, metadata["calibration_factors"])
    assert len(trace["trees"]) == metadata["tree_count"]
    assert np.isclose(trace["total_hours"], metadata["future_hours"], atol=0.01)
    assert np.isclose(trace["base_score"] * trace["factor_sum"], trace["base_hours"], atol=0.02)
    assert np.isclose(trace["base_hours"] + trace["tree_hours"], trace["total_hours"], atol=0.01)
    assert metadata["tree_count"] == model.num_boosted_rounds() == 1229
    routes = trace["routes"]
    assert (routes.groupby("arvore").pessoas.sum() == metadata["people"]).all()
    assert np.allclose(routes.groupby("arvore").efeito_horas.sum(), trace["trees"].efeito_horas)
    assert np.isclose(trace["contributions"].efeito_horas.sum(), trace["total_hours"], atol=0.02)
    assert "digraph Tree" in tree_diagram(trace["nodes"], 1229)
    with zipfile.ZipFile(io.BytesIO(audit_package(trace, model, "2026-10"))) as package:
        assert len(package.namelist()) == 7
        assert all(
            "cod_pessoa" not in package.read(name).decode("utf-8")
            for name in package.namelist()
            if not name.endswith(".gz")
        )


def test_recursive_projection_uses_previous_calibrated_predictions():
    meta = json.loads((ARTIFACTS / "metadata.json").read_text(encoding="utf-8"))
    features = pd.read_csv(ARTIFACTS / "projection_features.csv")
    forecast = pd.read_csv(ARTIFACTS / "forecast.csv")
    model = xgb.Booster()
    model.load_model(ARTIFACTS / "demo_model.json")
    assert len(forecast) == 12
    first = features.loc[features.ciclo.eq("2026-10")]
    following = features.loc[features.ciclo.eq("2026-11")]
    predicted = np.maximum(model.predict(_matrix(first)), 0) * first.funcao.map(
        meta["calibration_factors"]
    )
    np.testing.assert_allclose(following.horas_ciclo_anterior, predicted, atol=1e-6)
    assert np.isclose(predicted.sum(), forecast.horas_previstas.iloc[0], atol=0.01)
    last = features.loc[features.ciclo.eq(forecast.ciclo.iloc[-1])]
    trace = audit_demo(model, last, meta["calibration_factors"])
    assert np.isclose(trace["total_hours"], forecast.horas_previstas.iloc[-1], atol=0.01)
    assert cycle_label(pd.Period("2026-10")) == "16/09/2026 a 15/10/2026"


def test_streamlit_has_three_pages_and_labels_the_data_as_synthetic():
    app = AppTest.from_file(ROOT / "app.py", default_timeout=30).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Previsão",
        "Explicabilidade das árvores",
        "Como funciona o XGBoost",
    ]
    app.session_state["main_page"] = "Explicabilidade das árvores"
    app.run()
    assert not app.exception
    assert any("Como as árvores constroem" in item.value for item in app.subheader)
    app.session_state["main_page"] = "Como funciona o XGBoost"
    app.run()
    assert not app.exception
    assert any("apenas à simulação" in item.value for item in app.info)


def _trees_page():
    from dashboard.common import load_artifacts, version
    from dashboard.trees import render_trees

    signature = version()
    meta, tables = load_artifacts(signature)
    render_trees(meta, tables, signature)


def test_tree_page_controls_and_audit_exports():
    # AppTest does not serialize the active st.tabs widget on button reruns.
    # Exercise this page independently, with the same rendering and state.
    app = AppTest.from_function(_trees_page, default_timeout=40).run()
    assert not app.exception
    app.button(key="run_tree_audit").click().run()
    assert not app.exception
    assert any("Como chegamos à base" in item.value for item in app.markdown)
    app.button(key="load_tree_catalog").click().run()
    assert not app.exception
    app.selectbox(key="inspect_tree_id").select(1229).run()
    assert not app.exception
    app.selectbox(key="tree_audit_cycle").select("2027-09").run()
    app.button(key="run_tree_audit").click().run()
    assert not app.exception
