"""Which GPU tools work in cfl-model:1 on the GB10 (run with XLA_PYTHON_CLIENT_PREALLOCATE=false: vLLM shares the GPU)."""
import time
def t(name, fn):
    try:
        s = time.time(); r = fn(); print(f"OK   {name:6} {time.time()-s:6.2f}s  {r}")
    except Exception as e:
        print(f"FAIL {name:6} {type(e).__name__}: {str(e)[:160]}")
def torch_():
    import torch; x = torch.randn(4096, 4096, device="cuda"); return f"{torch.__version__} matmul sum {float((x@x).sum()):.1f}"
def jax_():
    import jax, jax.numpy as jnp
    x = jnp.ones((4096, 4096)); return f"{jax.__version__} {jax.devices()} sum {float((x@x).sum()):.0f}"
def cupy_():
    import cupy as cp; x = cp.arange(10_000_000, dtype=cp.float32); return f"{cp.__version__} sum {float(x.sum()):.3e}"
def cudf_():
    import cudf; d = cudf.DataFrame({"a": range(1_000_000)}); return f"{cudf.__version__} mean {float(d.a.mean())}"
def cuopt_():
    from cuopt.linear_programming import data_model, solver, solver_settings
    import numpy as np
    dm = data_model.DataModel()
    # max x+y s.t. x+2y<=4, 3x+y<=6, x,y>=0  -> min -x-y ; optimum x=1.6 y=1.2
    dm.set_csr_constraint_matrix(np.array([1.,2.,3.,1.]), np.array([0,1,0,1],dtype=np.int32), np.array([0,2,4],dtype=np.int32))
    dm.set_constraint_bounds(np.array([4.,6.])); dm.set_row_types(np.array(["L","L"]))
    dm.set_objective_coefficients(np.array([-1.,-1.]))
    dm.set_variable_lower_bounds(np.array([0.,0.])); dm.set_variable_upper_bounds(np.array([10.,10.]))
    sol = solver.Solve(dm, solver_settings.SolverSettings())
    return f"LP x={list(np.round(sol.get_primal_solution(),3))} (expect 1.6, 1.2)"
for n, fn in [("torch", torch_), ("jax", jax_), ("cupy", cupy_), ("cudf", cudf_), ("cuopt", cuopt_)]:
    t(n, fn)
