"""Phase 3 (OPTIONAL) — reproduce the paper's Table I statistical comparison.

Fit a logistic regression of correctness (0/1) on the approach/model, comparing each
config against the QueryCAD GPT-4o baseline, and report Odds Ratio + p-value.
Target headline: the top proprietary LLM -> OR ~1.93, p ~0.02, 62/111 correct.

Requires statsmodels + pandas (graphrag env). Input: per-question 0/1 correctness for
each config (from grade.py), long-format:  [config, correct].
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def compare(df: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """df columns: 'config' (categorical), 'correct' (0/1). Returns OR + p-value vs baseline."""
    df = df.copy()
    df["config"] = pd.Categorical(df["config"],
                                  categories=[baseline] + [c for c in df["config"].unique() if c != baseline])
    model = smf.logit("correct ~ C(config)", data=df).fit(disp=False)
    out = pd.DataFrame({
        "coef": model.params,
        "odds_ratio": np.exp(model.params),
        "p_value": model.pvalues,
    })
    return out
