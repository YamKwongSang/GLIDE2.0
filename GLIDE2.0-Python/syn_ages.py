import numpy as np
from numba import njit, prange

def syn_ages(m, p):
    print("syn_ages")
    # initialize fundamental variables like geothermal & chunk size
    geotherm = np.zeros(p.n)
    chunk = p.n
    mz = 211
    dz = p.zl / float(mz - 1)
    exhum = np.zeros(chunk)
    # calculate the time step satisfying Crank-Nicolson stability
    dt = dz * dz / p.kappa / 4.1
    tstart = 0.0
    tend = p.t_total
    nt = int(tend / dt) + 1
    # initialize sample depths, correlated with elevation
    m.depth = -1.0 * m.elev.copy()
    xtime = tend
    j = 0
    
    # backtrack to derive the initial burial depth for each sample
    while xtime > tstart:
        j += 1
        exhum, m.depth = loop1(m, p.m_max, xtime, exhum, dt, chunk)
        xtime -= dt
    nt = j
    
    xtime = tstart
    j = 0
    temp = np.zeros((mz, chunk))
    # set initial metrices for recording the thermal history
    for i in range(mz):
        temp[i, :] = p.Ts + float(i) / float(mz - 1) * (p.Tb - p.Ts)
    b_flux = (temp[mz-1, :] - temp[mz-2, :])
    # allocate large matrices for recording the thermal history
    temperature = np.zeros((nt, chunk))
    age = np.zeros(nt)
    deep = np.zeros((nt, chunk))
    steps_since_update = 0
    
    # start main time loop to solve the transient heat transfer equation
    while xtime < tend:
        # extract exhumation rate for the current time step
        exhum = loop2(m, p.m_max, xtime, exhum, chunk)
        temp = ftridag(p, temp, mz, chunk, exhum, dt, dz, b_flux)
        age[j] = tend - xtime
        # call JIT tridiagonal solver, update the temperature profile
        temperature = temper(temperature, m.depth, deep, temp, exhum, dt, dz, p.Tb, j, mz, chunk)
        xtime += dt
        j += 1
        # record depth and temperature for each time step
        steps_since_update += 1

    # find the closure depth
    for j_idx in range(chunk):
        iflag = m.isys[j_idx]
        # call Dodson's equation, calculate the cooling closure temperature
        Tc = dodson(temperature[:, j_idx], age, nt, iflag)
        if Tc==0:
            print("0!")
        found = False
        for i in range(nt):
            if temperature[i, j_idx] < Tc:
                if i == 0:
                    m.zcp[j_idx] = deep[i, j_idx]
                else:
                    # linear interpolation to pinpoint the closure depth
                    frac = (Tc - temperature[i, j_idx]) / (temperature[i-1, j_idx] - temperature[i, j_idx])
                    m.zcp[j_idx] = deep[i, j_idx] + frac * (deep[i-1, j_idx] - deep[i, j_idx])
                found = True
                break
        if not found:
            m.zcp[j_idx] = deep[nt-1, j_idx] if nt > 0 else 0.0
        # record the near-surface gradient
        geotherm[j_idx] = (temp[1, j_idx] - temp[0, j_idx]) / dz
    m.zz = np.maximum(0.01, m.elev + m.zcp)
    
    # calculate synthetic ages based on closure depths 
    m.syn_age = np.zeros(p.n)
    for i in range(p.n):
        dist = 0.0
        j_idx = p.m_max - 1
        while dist < m.zz[i]:
            m.syn_age[i] += m.tsteps[p.m_max - 1 - j_idx]
            dist += m.tsteps[p.m_max - 1 - j_idx] * m.edot_dat[j_idx + i * p.m_max]
            j_idx -= 1
        j_idx += 1
        dist -= m.tsteps[p.m_max - 1 - j_idx] * m.edot_dat[j_idx + i * p.m_max]
        m.syn_age[i] -= m.tsteps[p.m_max - 1 - j_idx]
        frac = (m.zz[i] - dist) / m.edot_dat[j_idx + i * p.m_max]
        m.syn_age[i] += frac
        
    # calculate misfit and R^2
    m.misfits = np.abs(m.syn_age - m.ta)
    misfit = np.sqrt(np.sum((m.misfits ** 2) / (m.a_error ** 2)) / float(p.n))
    ss_res = np.sum(m.misfits ** 2)
    ss_tot = np.sum((m.ta - np.mean(m.ta)) ** 2)
    R2 = 1 - ss_res / ss_tot
    return misfit, R2

@njit(parallel=True, fastmath=True)
def ftridag(p, u, n, chunk, exhum, dt, dz, b_flux):
    # calculate dimenionless time & space coefficients
    l_val = p.kappa * dt / (2.0 * dz * dz) # original: lambda
    # extract constants independent of row/col
    exhum_term = dt / (4.0 * dz)
    hp_dt = p.hp * dt
    mid_term = 1.0 - (2.0 * l_val)
    
    # introduce prange for multithreaded column parallelization
    for col in prange(chunk):
        # thread-local memory, improve cache hit rates
        a = np.empty(n)
        b = np.empty(n)
        c = np.empty(n)
        r = np.empty(n)
        gam = np.empty(n)
        # initialize boundary condition coefficients
        a[n-1] = 0.0
        b[0] = 1.0
        b[n-1] = 1.0
        c[0] = 0.0
        r[0] = p.Ts
        alpha = exhum[col] * exhum_term
        ax = alpha - l_val
        bx = 1.0 + (2.0 * l_val)
        cx = -1.0 * (l_val + alpha)
        l_minus_alpha = l_val - alpha
        l_plus_alpha = l_val + alpha
        
        # construct diagonals & right-hand constant terms of tridiagonal matrix
        for i in range(1, n - 1):
            a[i] = ax
            b[i] = bx
            c[i] = cx
            r[i] = l_minus_alpha * u[i-1, col] + mid_term * u[i, col] + l_plus_alpha * u[i+1, col] + hp_dt
        r[n-1] = u[n-2, col] + b_flux[col]
        
        # Thomas algorithm, forward elimination
        bet = b[0]
        u[0, col] = r[0] / bet
        for j in range(1, n):
            gam[j] = c[j-1] / bet
            bet = b[j] - a[j] * gam[j]
            u[j, col] = (r[j] - a[j] * u[j-1, col]) / bet
        # Thomas algorithm, back substitution
        for j in range(n-2, -1, -1):
            u[j, col] -= gam[j+1] * u[j+1, col]

    for col in range(chunk):
        u[0, col] = p.Ts
        u[n-1, col] = u[n-2, col] + b_flux[col]
    return u

@njit
def dodson(temp, time, nstep, iflag):
    # set activation energy, geometry factor & diffusion coefficients
    if iflag == 1:# AFT - Ketcham 1999, Reiners 2004
        energy, geom, diff = 147.0e3, 1.0, 2.05e6 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 2:# ZFT - Reiners 2004
        energy, geom, diff = 208.0e3, 1.0, 1.24e8 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 3:# AHe - Farley et al. 2000, Reiners 2004
        energy, geom, diff = 138.0e3, 1.0, 7.64e7 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 4:# ZHe - Reiners 2004
        energy, geom, diff = 169.0e3, 1.0, 7.03e5 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 5:# HAr - Harrison 1981, Reiners 200
        energy, geom, diff = 268.0e3, 1.0, 1320.0 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 6:# MAr - Hames & Bowring 1994, Robbins 1972, Reiners 2004
        energy, geom, diff = 180.0e3, 1.0,   3.91 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 7:# BAr - Grove & Harrison 1996, Reiners 2004
        energy, geom, diff = 197.0e3, 1.0,  733.0 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 8:# KAr
        energy, geom, diff = 183.0e3, 1.0, 5.39e5 * 3600.0 * 24.0 * 365.25e6
    else:
        raise ValueError("Unknown mineral type flag")
        
    r = 8.314
    # traverse cooling history backward to calculate dynamic closure temperature
    for i in range(nstep-1, 0, -1):
        if i == 0:
            cooling = (temp[1] - temp[0]) / (time[1] - time[0])
        elif i == nstep-1:
            cooling = (temp[i] - temp[i-1]) / (time[i] - time[i-1])
        else:
            cooling = (temp[i+1] - temp[i-1]) / (time[i+1] - time[i-1])
        cooling = max(cooling, 0.10)
        # Arrhenius relationships, closure temperature
        tau = r * (temp[i] + 273.0)**2 / (energy * cooling)
        closure = energy / (r * np.log(geom * tau * diff)) - 273.0
        if temp[i] > closure:
            return closure
        
    return closure

@njit
def temper(temperature, depth, deep, temp, exhum, dt, dz, Tb, j, mz, chunk):
    # track the depth grid, extract temperatures
    for i in range(chunk):
        depth[i] = depth[i] - exhum[i] * dt
        deep[j, i] = depth[i]
        k = max(0, int(depth[i] / dz))
        if k >= mz - 1:
            temperature[j, i] = Tb
        else:
            xint = (depth[i] - dz * float(k)) / dz
            temperature[j, i] = temp[k+1, i] * xint + temp[k, i] * (1.0 - xint)
    return temperature

@njit
def loop1(m, m_max, xtime, exhum, dt, chunk):
    # backtrack exhumation rates in inverse time steps
    pos = 0
    for i in range(len(m.tsteps_sum)):
        if m.tsteps_sum[i] >= xtime:
            pos = i
            break
    for i in range(chunk):
        exhum[i] = m.edot_dat[pos + i * m_max]
        m.depth[i] = m.depth[i] + exhum[i] * dt
    return exhum, m.depth

@njit
def loop2(m, m_max, xtime, exhum, chunk):
    # extract exhumation rates for the current forward calculation step
    pos = 0
    for i in range(len(m.tsteps_sum)):
        if m.tsteps_sum[i] >= xtime:
            pos = i
            break
    for i in range(chunk):
        exhum[i] = m.edot_dat[pos + i * m_max]
    return exhum
