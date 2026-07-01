import numpy as np
from numba import njit
from initool import closure_temp, time_end

def solve_inverse(m, p):
    print("solving inverse")
    # initialize matrices
    m.Y1 = np.zeros((p.n, p.n))
    m.B = np.zeros(p.n, dtype=int)
    m.II = np.eye(p.n)
    m.Y2 = np.zeros((p.n * p.m_max, p.n))
    # multiplication of covariance matrix and transposed design matrix
    m.Y2 = np.dot(m.cov, m.A.T)
    m.Y1 = np.dot(m.A, m.Y2)
    # add prior error variance to the diagonal for regularization
    for i in range(p.n):
        m.Y1[i, i] += (m.a_error[i] * p.edot_mean) ** 2
    # NumPy matrix inverse (replace dgetrf+dgetri)
    try: m.Y1 = np.linalg.inv(m.Y1)
    except np.linalg.LinAlgError:
        raise ValueError("Y1 is singular and cannot be inverted")

    m.Y2 = np.dot(m.A.T, m.Y1)
    # compute residuals between theoretical exhumation and actual elevation
    m.zz = np.dot(m.A, m.edot_pr)
    m.zz = (m.zc + m.elev) - m.zz
    m.BB = np.dot(m.Y2, m.zz)
    # exhumation at dummy points
    m.edot = post_edot(m, p)
    # constraint: truncated to 0
    m.edot[m.edot < 0.0] = 0.0
    # data covariance for real points
    m.H = np.dot(m.cov, m.Y2)
    m.zz = np.dot(m.A, m.edot_pr)
    m.zz = (m.zc + m.elev) - m.zz
    m.edot_dat = np.dot(m.H, m.zz) + m.edot_pr
    # constraint: truncated to 0
    m.edot_dat[m.edot_dat < 0.0] = 0.0
    return

@njit(fastmath = True)
def find_zc(m, p):
    mz = 131
    dz = p.zl / float(mz - 1) # spatial step size
    # initialize arrays
    temp_age = np.zeros(mz)
    tdot = np.zeros(mz)
    closure = np.zeros(mz)
    # initial time step satisfying von Neumann stability
    dt = (dz**2.0) / p.kappa / 4.1
    tstart = 0.0
    tend = p.t_total
    
    for kk in range(p.n):
        xtime = tstart
        # solve temperature field & cooling rate
        temp_age, tdot = time_end(mz, xtime, tend, m.ta, m.tsteps_sum, m.edot_dat,
                                  kk, p.m_max, p.kappa, p.Ts, p.Tb, p.hp, dt, dz)
        # clamp cooling rate to postive
        #tdot = np.maximum(tdot, 0.01)
        closure[:] = 0.0
        iflag = m.isys[kk]
        # compute simultaneous equations for closure depth zc & temperature Tc
        closure = closure_temp(tdot, temp_age, closure, iflag)
        for i in range(1, mz):
            if temp_age[i-1] > closure[i-1]:
                # linear interpolation slopes
                M = 1.0 * (dz / (closure[i-1] - closure[i-2]))
                P = 1.0 * (dz / (temp_age[i-1] - temp_age[i-2]))
                # intersection point for Tc
                Tc = ((M * closure[i-2]) - (P * temp_age[i-2])) / (M - P)
                xjunk = M * (Tc - closure[i-1])
                # record the final closure depth
                m.zc[kk] = dz * float(i-1) + xjunk
                break
    return

@njit
def post_edot(m, p):
    m_total = p.m_max * p.dummy
    edot = np.zeros(m_total)
    for i in range(m_total):
        ik = i // p.m_max
        xi, yi = m.x_dum[ik], m.y_dum[ik]
        # directly compute target offset, avoid if-statement in nested loop
        target = i % p.m_max
        dot_sum = 0.0
        # only iterate over real points (n), reduce complexity from O(n*m_max) to O(n)
        for k in range(p.n):
            j = k * p.m_max + target
            # compute Euclidean spatial distance
            dist = np.sqrt((xi-m.x[k]) **2 + (yi-m.y[k]) **2)
            # compute Gaussian spatial correlation weight and sum directly
            cmmj = p.sigma2 * np.exp(-dist / p.xL)
            dot_sum += cmmj * m.BB[j]
        # add the prior exhumation rate
        edot[i] = dot_sum + m.edot_pr_dum[i]
    return edot
