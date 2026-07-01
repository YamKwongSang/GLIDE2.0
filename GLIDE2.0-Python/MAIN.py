# MAIN.py
from time import time
import numpy as np
from JITclass import Parm, Matr, GlideConfig
from initialize_p import parameters
from build_m import matrices
from syn_ages import syn_ages
from solve_inverse import solve_inverse, find_zc
from post_res import posterior, posterior_dat
from write_output import write_output

def glide(cfg, log_callback=None, progress_callback=None):
    if isinstance(cfg, dict):
        cfg = GlideConfig(**cfg)
    if not isinstance(cfg, GlideConfig):
        raise TypeError("glide() expects a GlideConfig instance or a dict")
    def log(msg):
        if log_callback: log_callback(msg)
        else: print(msg)
    def update_progress(v):
        if progress_callback:
            progress_callback(v)

    m = Matr()
    p = Parm()
    t = time()
    log("Initializing parameters...")
    parameters(m, p, cfg)
    log(f"min age={np.min(m.ta)}, max age={np.max(m.ta)}")
    log(f"total ages {p.n}, dummy points={p.dummy}")
    log(f"AFT  \t{m.ages[0,1]:.3f} km  \t{m.ages[0,0]:.1f}°C")
    log(f"ZFT  \t{m.ages[1,1]:.3f} km  \t{m.ages[1,0]:.1f}°C")
    log(f"AHe  \t{m.ages[2,1]:.3f} km  \t{m.ages[2,0]:.1f}°C")
    log(f"ZHe  \t{m.ages[3,1]:.3f} km  \t{m.ages[3,0]:.1f}°C")
    update_progress(10)

    log("Building matrices...")
    matrices(m, p)
    m.edot[:] = p.edot_mean
    m.edot_dat = m.edot_pr
    update_progress(20)

    log("Calculating prior misfit...")
    mis0, R02 = syn_ages(m, p)
    log(f"Prior misfit = {mis0}")
    log(f"Prior R² = {R02}")
    update_progress(30)

    for i in range(int(cfg.iters)):
        log(f"Inverse iteration {i+1}/{int(cfg.iters)}")
        solve_inverse(m, p)
        find_zc(m, p)
        update_progress(30 + (i+1)/cfg.iters *60)

    log("Calculating posterior misfit...")
    mis1, R12 = syn_ages(m, p)
    log(f"Posterior misfit = {mis1}")
    log(f"Posterior R² = {R12}")
    update_progress(90)

    log("Computing posterior matrices...")
    posterior(m, p)
    
    flag = False
    if flag: posterior_dat(m, p, 1)
    update_progress(95)

    log("Writing outputs...")
    write_output(m, p)
    update_progress(100)
    log(f"FINISHED <(°O°)> {(time()-t)/60:.2f} min")
    print("\a")
    return {
        "prior misfit": mis0,
        "prior R²": R02,
        "post misfit": mis1,
        "post R²": R12,
    }


if __name__ == "__main__":
    # Example direct call:
    # cfg = GlideConfig(...).normalize()
    # glide(cfg)
    pass