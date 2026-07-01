import numpy as np
from numba import njit
@njit
def matrices(m, p):
#This function builds the forward operator, A & the covariance matrix, cov
#It also allocates matrices used in solve_inverse
    # initialize matrices
    m.A = np.zeros((p.n, p.n * p.m_max))
    m.edot = np.zeros(p.dummy * p.m_max)
    m.edot_dat = np.zeros(p.n * p.m_max)
    m.eps_dum = np.zeros(p.dummy * p.m_max)
    m.sf = np.zeros(p.dummy * p.m_max)
    m.cov = np.zeros((p.n * p.m_max, p.n * p.m_max)) # dtype=np.float32 for less memories
    m.H = np.zeros((p.n * p.m_max, p.n))
    m.Y2 = np.zeros((p.n * p.m_max, p.n))
    # build the matrix A (discretized ages)
    m.A[:, :] = 0.0
    
    for i in range(p.n):
        mi = 1
        k = 1
        summ = 0.0
        # calculate the number of time steps required and the remainder term
        while summ < m.ta[i]:
            summ += m.tsteps[mi-1]
            mi += 1
        mi -= 1
        if mi == 0:
            summ = 0.0
            rest = 0.0
        else:
            summ -= m.tsteps[mi-1]
            rest = m.ta[i] - summ
        k = 0
        # calculate loop boundaries
        start_j = (p.m_max - mi) + i * (p.m_max)
        end_j = i * (p.m_max -1) + p.m_max + i
        for j in range(start_j, end_j):
            k += 1
            m.A[i, j] = m.tsteps[mi-k]
            if k == 1:
                m.A[i, j] = rest
    
    # build the covariance matrices defining the spatial correlation
    m.cov[:, :] = 0.0
    # loop through lines of matrix
    for i in range(p.n * p.m_max):
        #ik = (i + p.m_max -1) // p.m_max
        ik = i // p.m_max
        jk = ik -1
        j_values = range(i, p.n * p.m_max, p.m_max)
        for j in j_values:
            jk +=1
            # calculate Euclidean distances between points
            #dist = np.sqrt((m.x[ik-1] - m.x[jk-1])**2 + 
            #              (m.y[ik-1] - m.y[jk-1])**2)
            dist = np.sqrt((m.x[ik]-m.x[jk])**2 + (m.y[ik]-m.y[jk])**2)
            # apply spatial correlation formula, exponential decay
            m.cov[i, j] = p.sigma2 * np.exp(-(dist / p.xL))
            # exploit symmtry of covariance matrix
            m.cov[j, i] = m.cov[i, j]
    return
