import numpy as np
from numba import njit, prange

#@njit
def posterior(m, p):
    """
    This routine calculates the posterior variance at the control points and temporal resolution
    Cee is the posterior variance at the control points
    ~ represents a parameter at a control point
    ^ represents a parameter at a data point
    C~~ is the covariance at control points
    G series of steps is used to calculate Cee outlined below
    Cee = C~~ - C~^G'(GCG'+Ce)**-1 GC^~
                     [    =Y1    ]
    Cee = C~~ - C~^ G'Y1 G C^~
                   [ =Y2]
    Cee = C~~ - C~^ Y2 G C^~
                     [Y3]
    In order not to build a full Cee matrix, which could be enormous ...
      we only calculate the diagonal terms of Cee
    Cm is a row of C^~ describing covariance of control point with data points
    Cee(i,i) = C(i,i) - Ci^  Y3 C^i
    where Ci^ is the covariance of control point i with data points
    Cee(i,i) = C(i,i) - Ci^  Y4
    Cee(i,i) = C(i,i) - Y5
    Different processors handle different control points
    For the resolution matrix
    R = C~^G'(GCG'+Ce)**-1 G 
    similarly a row of the resolution matrix
    R = Ci^ Y3
    Temporal resolution is calculated by integrating in space across time
    """
    print("  posterior")
    m.Y3 = np.dot(m.Y2, m.A)
    cdum = p.sigma2
    
    # allocate arrays
    m.sf = np.zeros_like(m.sf)
    # main computation loop
    m.eps_dum, m.sf = post_var(m.Y3, m.x_dum, m.y_dum, m.x, m.y, cdum, p.xL, p.n, p.dummy, p.m_max)
    return

@njit
def posterior_dat(m, p, post):
    print("  posterior_dat")
    N = p.n * p.m_max # total dimension
    m.cpost = np.zeros((N, N))
    m.eps = np.zeros(N)
    m.eps_dat = np.zeros(N)
    m.eps_res = np.zeros(N)
    chunk = 100 # for memory optimization
    m.Y3 = np.dot(m.A, m.cov)
    
    # chunk-based computation of posterior covariance to prevent OOM
    for i in range(0, N, chunk):
        end_i = min(i + chunk, N)
        # temp_cpost = H * Y3, local block
        temp_cpost = np.dot(m.H[i:end_i, :], m.Y3)
        # update posterior variance matrix
        m.cpost[i:end_i, :] = m.cov[i:end_i, :] - temp_cpost
    m.eps = np.sqrt(np.maximum(np.diag(m.cpost), 0.0))
    
    if post == 1:
        # compute Y4 and substract 1
        Y4 = np.dot(m.H, m.A)
        for k in range(Y4.shape[0]):
            Y4[k, k] -= 1.0
        # directly compute diagonal of residual covariance (Cres)
        diag_Cres = np.zeros(N)
        for i in range(0, N, chunk):
            end_i = min(i + chunk, N)
            # local computation of Y5
            Y5_chunk = np.dot(m.cov[i:end_i, :], Y4)
            for j in range(end_i - i):
                # sum(Y4^T * Y5), diagonal extraction
                diag_Cres[i + j] = np.sum(Y5_chunk[j, :] * Y4[:, i + j])
        # safe square root
        m.eps_res = np.sqrt(np.maximum(diag_Cres, 0.0))
        # diagonal of observation error covariance (Cee)
        diag_Cee = (m.a_error * p.edot_mean) ** 2
        # Y6 = Cee * H, use broadcasting via diagonal
        Y6 = m.H * diag_Cee
        # diagonal of Cdata
        diag_Cdata = np.sum(m.H * Y6, axis=1)
        # final data error, safe square root
        m.eps_dat = np.sqrt(np.maximum(diag_Cdata, 0.0))
        
    return

@njit(fastmath=True, parallel=True)
def post_var(Y3, xd, yd, x, y, cdum, xL, n, D, M):
    DM = D * M
    # precompute control point indices
    control_i = np.zeros(DM, dtype=np.int32)
    for i in range(DM):
        control_i[i] = i // M
    Cee = np.empty(DM)
    t_res = np.empty(DM)
    
    # precompute the column sums of Y3
    Y3_col_sum = np.zeros(Y3.shape[1])
    for j in range(Y3.shape[1]):
        s = 0.0
        for i in range(Y3.shape[0]):
            s += Y3[i, j]
        Y3_col_sum[j] = s
        
    # cache spatial covariance matrix
    # ik spans up to D-1, precompute the (D,n) matrix to avoid repeats
    Cm_all = np.empty((D, n))
    for ik in prange(D):
        for k in range(n):
            dist = np.sqrt((xd[ik] - x[k])**2 + (yd[ik] - y[k])**2)
            Cm_all[ik, k] = cdum * np.exp(-dist / xL)

    # distributive property for subset summation
    # precompute sums required for temporal resolution t_res
    Y3_subset_sum = np.zeros((M, n))
    for m_step in range(M):
        for p in range(n):
            col_idx = m_step + p * M
            s = 0.0
            for k in range(n):
                row_idx = m_step + k * M
                s += Y3[row_idx, col_idx]
            Y3_subset_sum[m_step, p] = s

    # pure scalar operations
    for i in prange(D * M):
        ik = control_i[i]
        m_step = i % M  # renamed to m_step
        # modified Y5 computation
        y5_val = 0.0
        for k in range(n):
            idx = m_step + k * M
            # directly lookup for precomputed Cm_all & Y3_col_sum
            y5_val += (Cm_all[ik, k]**2) * Y3_col_sum[idx]
        Cee[i] = np.sqrt(cdum - y5_val)
        # modified temporal resolution t_res calculation
        res_val = 0.0
        for p in range(n):
            # combine precomputed Cm_all & Y3_subset_sum to acheieve 
            res_val += Cm_all[ik, p] * Y3_subset_sum[m_step, p]
        t_res[i] = res_val
        
    return Cee, t_res