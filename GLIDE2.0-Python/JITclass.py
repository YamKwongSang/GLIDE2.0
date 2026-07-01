import numpy as np
from numba import int64, float64, types, float32
from numba.experimental import jitclass
from dataclasses import dataclass
from pathlib import Path

parm_spec = [
    ('run', types.unicode_type),
    ('topofile', types.unicode_type),
    ('lon1', float32),
    ('lon2', float32),
    ('lat1', float32),
    ('lat2', float32),
    ('edot_mean', float64),
    ('sigma2', float32),
    ('xL', float32),
    ('angle', float32),
    ('aspect', float32),
    ('deltat', float32),
    ('t_total', float32),
    ('zl', float32),
    ('Ts', float32),
    ('Tb', float32),
    ('kappa', float32),
    ('hp', float32),
    ('iflag_error', int64),
    ('n', int64),
    ('contr', int64),
    ('dummy', int64),
    ('m_max', int64),
    ('nx_dum', int64), ('ny_dum', int64),
    ('nx', int64), ('ny', int64)
]

@jitclass(parm_spec)
class Parm:
    def __init__(self):
        self.run = ''
        self.topofile = ''
        self.lon1 = 0.0
        self.lon2 = 0.0
        self.lat1 = 0.0
        self.lat2 = 0.0
        self.edot_mean = 0.0
        self.sigma2 = 0.0
        self.xL = 0.0
        self.angle = 0.0
        self.aspect = 0.0
        self.deltat = 0.0
        self.t_total = 0.0
        self.zl = 0.0
        self.Ts = 0.0
        self.Tb = 0.0
        self.kappa = 0.0
        self.hp = 0.0
        self.iflag_error = 0
        self.n = 0
        self.contr = 7
        self.dummy = 0
        self.m_max = 0
        self.nx_dum = 0
        self.ny_dum = 0
        self.nx = 0
        self.ny = 0

matr_spec = [
    ('ta', float64[:]),
    ('a_error', float64[:]),
    ('zc', float64[:]),
    ('zcp', float64[:]),
    ('x', float64[:]),
    ('y', float64[:]),
    ('elev', float64[:]),
    ('elev_true', float64[:]),
    ('x_true', float64[:]),
    ('y_true', float64[:]),
    ('misfits', float64[:]),
    ('syn_age', float64[:]),
    ('isys', int64[:]),
    ('depth1', float64[:]),
    ('depth', float64[:]),
    ('zz', float64[:]),
    ('x_dum', float64[:]),
    ('y_dum', float64[:]),
    ('x_dum_true', float64[:]),
    ('y_dum_true', float64[:]),
    ('tsteps', float64[:]),
    ('tsteps_sum', float64[:]),
    ('edot_pr', float64[:]),
    ('edot_pr_dum', float64[:]),
    ('nsystems', int64[:]),
    ('ages', float64[:, :]),
    ('A', float64[:, :]),
    ('edot', float64[:]),
    ('edot_dat', float64[:]),
    ('eps_dum', float64[:]),
    ('eps', float64[:]),
    ('sf', float64[:]),
    ('cov', float64[:, :]), # float32 for less memories
    ('cpost', float64[:, :]),
    ('eps_dat', float64[:]),
    ('eps_res', float64[:]),
    ('H', float64[:, :]),
    ('Y2', float64[:, :]),
    ('Y1', float64[:, :]),
    ('B', int64[:]),
    ('II', float64[:, :]),
    ('BB', float64[:]),
    ('Y3', float64[:, :]),
    ('Y4', float64[:, :]),
    ('Y5', float64[:, :]),
    ('Y6', float64[:, :]),
]

@jitclass(matr_spec)
class Matr:
    def __init__(self):
        f_arr1 = np.empty(0, dtype=np.float64)
        f_arr2 = np.empty((0, 0), dtype=np.float64)
        #for less memories
        #f_arr3 = np.empty((0, 0), dtype=np.float32)
        i_arr1 = np.empty(0, dtype=np.int64)

        self.ta = f_arr1
        self.a_error = f_arr1
        self.zc = f_arr1
        self.zcp = f_arr1
        self.x = f_arr1
        self.y = f_arr1
        self.elev = f_arr1
        self.elev_true = f_arr1
        self.x_true = f_arr1
        self.y_true = f_arr1
        self.misfits = f_arr1
        self.syn_age = f_arr1
        self.isys = i_arr1
        self.depth1 = f_arr1
        self.depth = f_arr1
        self.zz = f_arr1
        self.x_dum = f_arr1
        self.y_dum = f_arr1
        self.x_dum_true = f_arr1
        self.y_dum_true = f_arr1
        self.tsteps = f_arr1
        self.tsteps_sum = f_arr1
        self.edot_pr = f_arr1
        self.edot_pr_dum = f_arr1
        self.nsystems = i_arr1
        self.ages = f_arr2
        self.A = f_arr2
        self.edot = f_arr1
        self.edot_dat = f_arr1
        self.eps_dum = f_arr1
        self.eps = f_arr1
        self.sf = f_arr1
        self.cov = f_arr2 #f_arr3 for less memories
        self.cpost = f_arr2
        self.eps_dat = f_arr1
        self.eps_res = f_arr1
        self.H = f_arr2
        self.Y2 = f_arr2
        self.Y1 = f_arr2
        self.B = i_arr1
        self.II = f_arr2
        self.BB = f_arr1
        self.Y3 = f_arr2
        self.Y4 = f_arr2
        self.Y5 = f_arr2
        self.Y6 = f_arr2
        
@dataclass
class GlideConfig:
    run_folder: str
    topofile: str
    data_file: str
    nx: int
    ny: int
    iters: int
    lon1: float
    lon2: float
    lat1: float
    lat2: float
    edot_mean: float
    sigma: float
    xL: float
    deltat: float
    t_total: float
    zl: float
    Ts: float
    Tb: float
    kappa: float
    hp: float
    spacin: float
    grad: float
    def normalize(self) -> "GlideConfig":
        self.run_folder = str(Path(self.run_folder).expanduser().resolve())
        self.topofile = str(Path(self.topofile).expanduser().resolve())
        self.data_file = str(Path(self.data_file).expanduser().resolve())
        return self