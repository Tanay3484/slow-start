"""Download the TabPFN v2 weights (Apache 2.0) into the model cache. The Dockerfile runs this at build time
so a restart never downloads anything, and so the licence-gated 2.5+ weights are never fetched.

    TABPFN_MODEL_CACHE_DIR=/opt/tabpfn python scripts/bake_tabpfn.py
"""

import numpy as np
from tabpfn import TabPFNRegressor
from tabpfn.constants import ModelVersion

reg = TabPFNRegressor.create_default_for_version(ModelVersion.V2, device="cpu", n_estimators=1)
reg.fit(np.random.rand(30, 4), np.random.rand(30))
reg.predict(np.random.rand(3, 4), output_type="quantiles", quantiles=[0.3, 0.5])
print("TabPFN v2 weights ready")
