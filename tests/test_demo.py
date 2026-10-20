import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from streamlit.testing.v1 import AppTest

from demo_pipeline import FEATURES, audit_demo, synthetic_panel

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
    assert np.isclose(
        trace["base_score"] * trace["factor_sum"], trace["base_hours"], atol=0.02
    )
    assert np.isclose(
        trace["base_hours"] + trace["tree_hours"], trace["total_hours"], atol=0.01
    )


def test_streamlit_has_three_pages_and_labels_the_data_as_synthetic():
    app = AppTest.from_file(ROOT / "app.py", default_timeout=30).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Previsão",
        "Explicabilidade das árvores",
        "Como funciona",
    ]
    app.session_state["main_page"] = "Explicabilidade das árvores"
    app.run()
    assert not app.exception
    assert any("A conta, passo a passo" in item.value for item in app.markdown)
    app.session_state["main_page"] = "Como funciona"
    app.run()
    assert not app.exception
    assert any("apenas à simulação" in item.value for item in app.info)
