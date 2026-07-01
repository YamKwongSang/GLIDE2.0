import numpy as np
from numba import njit

@njit
def closure_temp(cooling, temp, closure, iflag):
    # Initialize parameters based on iflag
    if iflag == 1:
        # AFT from Ketcham 1999, taken from Reiners 2004
        energy, geom, diff = 147.0e3, 1.0, 2.05e6 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 2:
        # ZFT from Reiners 2004
        energy, geom, diff = 208.0e3, 1.0, 1.24e8 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 3:
        # AHe from Farley et al. 2000, taken from Reiners 2004
        energy, geom, diff = 138.0e3, 1.0, 7.64e7 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 4:
        # ZHe from Reiners 2004
        energy, geom, diff = 169.0e3, 1.0, 7.03e5 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 5:
        # hbl from Harrison 1981, taken from Reiners 2004
        energy, geom, diff = 268.0e3, 1.0, 1320.0 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 6:
        # mus from Hames&Bowring 1994, Robbins 1972, taken from Reiners 2004
        energy, geom, diff = 180.0e3, 1.0, 3.91 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 7:
        # bio from Grove&Harrison 1996, taken from Reiners 2004
        energy, geom, diff = 197.0e3, 1.0, 733.0 * 3600.0 * 24.0 * 365.25e6
    elif iflag == 8:
        # kfs from Grove&Harrison1996, taken from Reiners 2004
        energy, geom, diff = 183.0e3, 1.0, 5.39e5 * 3600.0 * 24.0 * 365.25e6
    else:
        raise ValueError(f"Invalid iflag value: {iflag}")
    r = 8.314 # gas constant
    cooling_clipped = np.maximum(cooling, 0.10) # ensure cooling is at least 0.1 degC/Myr
    temp_kelvin = temp + 273.0 # temperature from Celsius to Kelvin
    tau = r * temp_kelvin**2 / energy / cooling_clipped
    closure = energy / r / np.log(geom * tau * diff) - 273.0
    return closure

@njit
def wave(a, size, factor, ny, nx, kdy, kdx, pec, A_o, depth):
# Wavenumber calculation & frequency domain filter
# Contains original 'kvalue' function
    for j in range(size):
        for i in range(size):
            a[i, j] = a[i, j] * factor
            # get wavenumber values
            nyqy = ny//2 +1
            nxqx = nx//2 +1
            # compute kx & ky coordinate, equivalent of 'kvalue'
            fj = j * kdy if j <= nyqy else (j - ny) * kdy
            fi = i * kdx if i <= nxqx else (i - nx) * kdx
            # total wave decay magnitude
            decay = np.sqrt(fj*fj + fi*fi)
            # apply heat advection & diffusion filter formulation
            manck = pec + np.sqrt(pec*pec + (2.0*np.pi* decay) **2)
            if decay == 0.0:
                manck = 2.0* pec
            # final amplitude coefficient for the wavenumber
            A_k = A_o * np.exp(-1.0* manck * depth)
            a[i, j] = a[i, j] * A_k
    return a

@njit(fastmath=True)
def time_end(n, xtime, tend, ta, tsteps_sum, edot, kk, m_max, kappa, Ts, Tb, hp, dt, dz):
    # solves 1D heat transfer equation over time
    temp_age = np.zeros(n)
    temp_pr = np.zeros(n)
    tdot = np.zeros(n)
    # initial linear geothermal gradient
    u = np.linspace(Ts, Tb, n)
    b_flux = u[n-1] - u[n-2] # bottom boundary heat flux
    
    # arrays for Thomas algorithm (Tridiagonal matrix)
    a, b, c, r = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    gam = np.empty(n)
    kappa_term = kappa / (2.0 * dz * dz)
    exhum_term_base = 1.0 / (4.0 * dz)
    exit_f = False
    
    # time-stepping loop
    while xtime < tend:
        # optimized lookup: binary search for exhumation rate
        idx = np.searchsorted(tsteps_sum, xtime, side='left')
        pos = idx if idx < len(tsteps_sum) else len(tsteps_sum) - 1
        exhum = edot[pos + kk * m_max]
        l_val = kappa_term * dt
        alpha = exhum * exhum_term_base * dt
        # matrix coefficients for Crank-Nicolson scheme
        ax = alpha - l_val
        bx = 1.0 + (2.0 * l_val)
        cx = -1.0 * (l_val + alpha)
        c1 = l_val - alpha
        c2 = 1.0 - (2.0 * l_val)
        c3 = l_val + alpha
        hpdt = hp *dt
        for i in range(1, n - 1):
            a[i] = ax
            b[i] = bx
            c[i] = cx
            # right-hand side vector
            r[i] = c1 * u[i-1] + c2 * u[i] + c3 * u[i+1] + hpdt
        
        # boundary conditions
        a[n-1] = 0.0
        b[0] = 1.0
        b[n-1] = 1.0
        c[0] = 0.0
        r[0] = Ts
        r[n-1] = u[n-2] + b_flux
        if b[0] == 0.0:
            raise ValueError('in tridag')
        bet = b[0]
        u[0] = r[0] / bet
        # Thomas algorithm: forward elimination
        for j in range(1, n):
            gam_j = c[j-1] / bet
            bet = b[j] - a[j] * gam_j
            gam[j] = gam_j
            if bet == 0.0:
                raise ValueError('tridag failed')
            u[j] = (r[j] - a[j] * u[j-1]) / bet
        
        # Thomas algorithm: backward substitution
        for j in range(n-2, -1, -1):
            u[j] -= gam[j+1] * u[j+1]
        u[0] = Ts
        u[n-1] = u[n-2] + b_flux
        xtime += dt
        if exit_f:
            temp_age[:] = u[:]
            break
            
        # adjust dt for the exact time step before measured age
        if tend - xtime - dt < ta[kk]:
            dt = tend - xtime - ta[kk]
            # reuse binary search for updated exhumation
            idx = np.searchsorted(tsteps_sum, xtime, side='left')
            pos = idx if idx < len(tsteps_sum) else len(tsteps_sum) - 1
            exhum = edot[pos + kk * m_max]
            temp_pr[:] = u[:] # store previous temperature profile
            exit_f = True
    #tdot_dist = exhum * dt
    tdot_factor = exhum / dz
    
    # compute cooling rate
    for i in range(n-1):
        #tdot[i] = (temp_age[i] - temp_pr[i] + (temp_pr[i+1] - temp_pr[i]) * (tdot_dist / dz)) / dt
        tdot[i] = (temp_age[i] - temp_pr[i]) / dt + (temp_pr[i+1] - temp_pr[i]) * tdot_factor
    return temp_age, tdot

@njit
def bilinear(u, t, zc, depth1, s, elev, melev, idx, i, i1, j1):
# Extracted modular function for bilinear interpolation
    zc[i] = ((1.0-u)*(1.0-t)*s[i1+1,j1+1,idx] +
             (1.0-u)*   t   *s[i1+1, j1 ,idx] +
                u   *   t   *s[ i1 , j1 ,idx] +
                u   *(1.0-t)*s[ i1 ,j1+1,idx])
    depth1[i] = ((1.0-u)*(1.0-t)*elev[i1+1,j1+1] +
                 (1.0-u)*   t   *elev[i1+1, j1 ] +
                    u   *   t   *elev[ i1 , j1 ] +
                    u   *(1.0-t)*elev[ i1 ,j1+1] - melev[i])
    return zc, depth1

@njit
def herror(A):
    n,m = A.shape
    err = 0.0
    for i in range(n):
        for j in range(m):
            ii = (-i)%n
            jj = (-j)%m
            err = max(err,
                      abs(A[ii,jj]-np.conj(A[i,j])))
    return err