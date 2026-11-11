# cfl-model: house model calibration + scenario simulation (Craig 5 Nov 2026: "train our model on 10 million scenarios
# on the spark.. pilot some GPU tools"). Base = NVIDIA PyTorch 25.09 (CUDA 13, aarch64, GB10). Each GPU library is
# optional so a missing aarch64 wheel does not stop the build; tools/probe.py reports what actually works.
FROM nvcr.io/nvidia/pytorch:25.09-py3
RUN pip install --no-cache-dir pandas pyarrow scikit-learn statsmodels
RUN pip install --no-cache-dir "jax[cuda13]" || echo "JAX cuda13 unavailable"
RUN pip install --no-cache-dir cupy-cuda13x || echo "cupy unavailable"
RUN pip install --no-cache-dir --extra-index-url=https://pypi.nvidia.com cudf-cu13 || echo "cudf unavailable"
RUN pip install --no-cache-dir --extra-index-url=https://pypi.nvidia.com cuopt-cu13 || echo "cuopt unavailable"
WORKDIR /work
