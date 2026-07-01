import numpy as np
import math
import csv
from numba import njit, objmode
import os
from JITclass import Parm, Matr, GlideConfig
from initool import closure_temp, wave, bilinear, time_end

def parameters(m: Matr, p: Parm, cfg: GlideConfig):
    print("Initializing parameters")
    cfg = cfg.normalize()
    p.run = cfg.run_folder
    p.topofile = cfg.topofile
    p.nx = int(cfg.nx)
    p.ny = int(cfg.ny)
    p.lon1 = float(cfg.lon1)
    p.lon2 = float(cfg.lon2)
    p.lat1 = float(cfg.lat1)
    p.lat2 = float(cfg.lat2)
    p.edot_mean = float(cfg.edot_mean)
    p.sigma2 = float(cfg.sigma)*float(cfg.sigma)
    p.xL = float(cfg.xL)
    p.deltat = float(cfg.deltat)
    p.t_total = float(cfg.t_total)
    p.zl = float(cfg.zl)
    p.Ts = float(cfg.Ts)
    p.Tb = float(cfg.Tb)
    p.kappa = float(cfg.kappa)
    p.hp = float(cfg.hp)
    spacin = float(cfg.spacin)
    # Create output folder if it does not exist
    os.makedirs(p.run, exist_ok=True)
    pi = math.pi
    colat = math.cos(((p.lat1 + p.lat2) / 2.0) * pi / 180.0)
    xl = (p.lon2 - p.lon1) * 111.111 * colat
    yl = (p.lat2 - p.lat1) * 111.111
    p.nx_dum = int(xl / spacin) + 1
    p.ny_dum = int(yl / spacin) + 1
    p.dummy = p.nx_dum * p.ny_dum
    xl_step = (p.lon2 - p.lon1) / float(p.nx_dum)
    yl_step = (p.lat2 - p.lat1) / float(p.ny_dum)
    
    methodname = {"AFT": 1, "ZFT": 2, "AHE": 3, "ZHE": 4,
                  "HAR": 5, "MAR": 6, "BAR": 7, "KAR": 8}
    required_cols = {"longitude", "latitude", "elevation",
                     "age", "std", "method"}
    data = []
    with open(cfg.data_file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = required_cols - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"CSV file is missing required columns: {sorted(missing)}")
        for row in reader:
            lo = float(row["longitude"])
            la = float(row["latitude"])
            tmp1 = float(row["elevation"])
            tmp2 = float(row["age"])
            tmp3 = float(row["std"])
            method = row["method"].strip().upper()
            sys_val = methodname[method]
            if lo > 180.0: lo -= 360.0
            if (tmp2 <= p.t_total and p.lon1 <= lo <= p.lon2
                and p.lat1 <= la <= p.lat2):
                data.append((lo, la, tmp1, tmp2, tmp3, sys_val))

    p.n = len(data)
    m.ta = np.zeros(p.n)
    m.a_error = np.zeros(p.n)
    m.zc = np.zeros(p.n)
    m.zcp = np.zeros(p.n)
    m.x = np.zeros(p.n)
    m.y = np.zeros(p.n)
    m.elev = np.zeros(p.n)
    m.elev_true = np.zeros(p.n)
    m.x_true = np.zeros(p.n)
    m.y_true = np.zeros(p.n)
    m.misfits = np.zeros(p.n)
    m.syn_age = np.zeros(p.n)
    m.isys = np.zeros(p.n, dtype=np.int64)
    m.depth1 = np.zeros(p.n)
    m.depth = np.zeros(p.n)
    m.zz = np.zeros(p.n)
    m.x_dum = np.zeros(p.dummy)
    m.y_dum = np.zeros(p.dummy)
    m.x_dum_true = np.zeros(p.dummy)
    m.y_dum_true = np.zeros(p.dummy)
    for i, (lo, la, tmp1, tmp2, tmp3, sys_val) in enumerate(data):
        m.x[i] = lo
        m.y[i] = la
        m.elev[i] = tmp1
        m.ta[i] = tmp2
        m.a_error[i] = tmp3
        m.isys[i] = sys_val
    m.elev_true = m.elev.copy()
    k = 0
    for i in range(p.nx_dum):
        for j in range(p.ny_dum):
            m.x_dum[k] = p.lon1 + float(i) * xl_step
            m.y_dum[k] = p.lat1 + float(j) * yl_step
            k += 1

    # Keep original coordinates
    m.x_dum_true = m.x_dum.copy()
    m.y_dum_true = m.y_dum.copy()
    m.x_true = m.x.copy()
    m.y_true = m.y.copy()

    # Convert dummy grid to local Cartesian coordinates
    for i in range(p.dummy):
        m.x_dum[i] = (m.x_dum[i] - p.lon1) * 111.11 * colat
        m.y_dum[i] = (m.y_dum[i] - p.lat1) * 111.11

    skip = 1
    nx0 = int(cfg.nx)
    ny0 = int(cfg.ny)
    nx = (nx0 - 1) // skip + 1
    ny = (ny0 - 1) // skip + 1

    lon_full = np.zeros((nx0, ny0))
    lat_full = np.zeros((nx0, ny0))
    topob_full = np.zeros((nx0, ny0))

    with open(p.topofile, "r", encoding="utf-8") as f:
        for j in range(ny0 - 1, -1, -1):
            for i in range(nx0):
                line = f.readline()
                parts = line.split()
                if len(parts) > 2:
                    lon_full[i, j] = float(parts[0])
                    lat_full[i, j] = float(parts[1])
                    topob_full[i, j] = float(parts[2])

    # Subsample topography
    lon = np.zeros((nx, ny))
    lat = np.zeros((nx, ny))
    topob = np.zeros((nx, ny))

    for j in range(0, ny0, skip):
        for i in range(0, nx0, skip):
            ii = i // skip
            jj = j // skip
            if ii < nx and jj < ny:
                lon[ii, jj] = lon_full[i, j]
                lat[ii, jj] = lat_full[i, j]
                topob[ii, jj] = topob_full[i, j]

    # ---------------------------------------
    # Time stepping
    # ---------------------------------------
    p.m_max = int(p.t_total / p.deltat) + 1
    m.tsteps = np.full(30, p.deltat)
    m.tsteps_sum = np.zeros(30)
    m.tsteps_sum[0] = m.tsteps[0]

    for i in range(1, 30):
        m.tsteps_sum[i] = m.tsteps_sum[i-1] + m.tsteps[i]

    summ = 0.0
    k = 1
    p.m_max = 0
    while summ < p.t_total and k < 30:
        summ += m.tsteps[k]
        k += 1
    p.m_max = k

    m.edot_pr = np.empty(p.n * p.m_max)
    m.edot_pr_dum = np.empty(p.dummy * p.m_max)

    # ---------------------------------------
    # Prior exhumation rate model
    # ---------------------------------------
    xtime = p.t_total
    for j in range(p.m_max):
        xtime = xtime - p.deltat
        for i in range(p.n):
            index = j + i * p.m_max
            m.edot_pr[index] = p.edot_mean
        for i in range(p.dummy):
            index = j + i * p.m_max
            m.edot_pr_dum[index] = p.edot_mean

    # ---------------------------------------
    # Thermochronometric system counts
    # ---------------------------------------
    m.nsystems = np.zeros(8, dtype=np.int64)
    for i in range(p.n):
        m.nsystems[m.isys[i] - 1] += 1

    m.ages = np.zeros((8, 5))

    # ---------------------------------------
    # Thermal correction
    # ---------------------------------------
    mean_elev = np.mean(topob)
    p.Ts = p.Ts - mean_elev * cfg.grad /1000
    p.zl = p.zl + (mean_elev / 1000.0)

    print("  prior_zc")
    prior_zc(m, p)

    m.zz = m.zc.copy()
    m.zc = np.zeros(p.n)

    # Remove mean from samples and topography
    topob = topob - mean_elev
    m.elev = m.elev - mean_elev

    print("  isotherm")
    isotherm(m, p, nx, ny, topob, lon, lat)

    # Convert samples to local coordinates and adjust elevation
    for i in range(p.n):
        m.x[i] = (m.x_true[i] - p.lon1) * 111.11 * colat
        m.y[i] = (m.y_true[i] - p.lat1) * 111.11
        m.elev[i] = (m.elev[i] - m.zc[i]) / 1000.0

    m.zc = m.zz.copy()
    return

@njit
def prior_zc(m, p):
#This subroutine calculates closure depths 
# The routine proceeds as follows
# For each sample do  
# Set up initial conditions, a linear increase of temperature with depth ...
#  ... use crank-nicholson finite differencing to step through time  
#  ... at the time equivalent to the measured age record the materical derivatives
#  ... use these cooling rates to estimate closure temperatures
#  ... find location in depth where closure depth is equal to temperature
# Determine average closure depth for each system, ie AFT
# also record other parameters for use in isotherms

    mz = 131 # number of depth nodes
    dz = p.zl/float(mz-1)
    temp_age = np.zeros(mz)
    tdot = np.zeros(mz)
    closure = np.zeros(mz)
    dt = (dz*dz / p.kappa) /4.0
    #skip = np.argmin(m.ta)
    tstart = 0.0
    tend = p.t_total
    xtime = tstart
    
    # loop through all sample data points
    for kk in range(p.n):
        # solve transient heat equation until the measured age
        temp_age, tdot = time_end(mz, xtime, tend, m.ta, m.tsteps_sum, m.edot_pr,
                                  kk, p.m_max, p.kappa, p.Ts, p.Tb, p.hp, dt, dz)
        iflag = m.isys[kk]
        # compute cooling rate-dependent closure temperatures
        closure = closure_temp(tdot, temp_age, closure, iflag)
        
        # find the specific depth where temperature equals closure temperature
        for i in range(1, mz):
            if temp_age[i-1] > closure[i-1]:
                # coefficients for linear interpolation
                M = 1.0* (dz / (closure[i-1] - closure[i-2]))
                P = 1.0* (dz / (temp_age[i-1] - temp_age[i-2]))
                # interpolated closure temperature
                Tc = ((M * closure[i-2]) - (P * temp_age[i-2])) / (M - P)
                xjunk = M * (Tc - closure[i-1])
                iidx = iflag - 1
                m.ages[iidx, 0] += Tc #closure temp
                m.ages[iidx, 1] += dz * float(i-1) + xjunk #closure depth
                m.ages[iidx, 2] += m.ta[kk] #age
                m.ages[iidx, 3] += (temp_age[1] - temp_age[0]) / dz #dT/dz|z=0
                m.ages[iidx, 4] += (temp_age[i-1] - temp_age[i-2]) / dz #dT/dz|z=zc
                m.zc[kk] = dz * float(i-1) + xjunk
                break # exit loop once intersection is found
    
    # vectorized averaging for each system
    mask = m.nsystems > 0
    m.ages[mask, :] = m.ages[mask, :] / m.nsystems[mask, np.newaxis]
    m.ages[~mask, :] = np.nan
    return

@njit
def isotherm(m, p, nx, ny, elev, lon, lat):
#This routine calculates the perturbation of isotherms due to topography.
#This is solved in frequency space so the code proceeds as follows:
#    embed topography in a power of 2 grid
#    apply taper to reduce edge effects
#    take the discreet fourier transform (2D)
#    loop through the number of systems used
#    apply continuation function
#    inverse fourier transform (2D)
    ymin = np.min(lat)
    xmin = np.min(lon)
    xlat = ymin
    xlon = xmin
    
    # minimum power of 2 that's suitable for FFT
    nx_2 = 2** int(np.ceil(np.log2(nx*2)))
    ny_2 = 2** int(np.ceil(np.log2(ny*2)))
    ny_2 = max(nx_2, ny_2)
    nx_2 = ny_2
    # needed to embed topography centrally
    nx1 = (nx_2 - nx)//2
    ny1 = (ny_2 - ny)//2
    size = ny_2
    a = np.zeros((size, size), dtype=np.complex64)
    a_ffted = np.zeros((size, size), dtype=np.complex64)
    # embed topography in a 2**nx_2 x 2**ny_2 grid
    a[nx1-1:nx1+nx-1, ny1-1:ny1+ny-1] = elev.astype(np.complex64)
    # taper topography to reduce edge effects (linear tapering)
    for i in range(nx1): #left edge
        a[i, :] = a[nx1-1, :] * ((i+1) / nx1)
    for i in range(nx_2 - nx1 -1, nx_2): #right edge
        a[i, :] = a[nx_2 - nx1 -1, :] * ((nx_2 - i -1) / nx1)
    for j in range(ny1): #bottom edge
        a[:, j] = a[:, ny1-1] * ((j+1) / ny1)
    for j in range(ny_2 - ny1 -1, ny_2): #top edge
        a[:, j] = a[:, ny_2 - ny1 -1] * ((ny1 - j -1) / ny1)

    # grid spacing in degrees
    dx = lon[nx//2, ny//2] - lon[nx//2 -1, ny//2]
    dy = lat[nx//2, ny//2] - lat[nx//2, ny//2 -1]
    # size of region in meters
    yl = dy * (ny -1) *111111.1
    xl = dx * (nx -1) *111111.1* np.cos(np.radians((np.min(lat) + np.max(lat)) /2.0))
    # grid spacing in meters
    xstep = xl / (nx -1)
    ystep = yl / (ny -1)
    # size of FFT grid
    xl = (nx_2 -1) * xstep
    yl = (ny_2 -1) * ystep
    # 2D FFT using Numba's object mode
    with objmode(a_ffted='complex64[:,:]'):
        a_ffted = np.fft.fft2(a)

    factor = 1.0/ (size*size)
    # grid spacing in meters
    dx = xstep
    dy = ystep
    # grid spacing in cycles/m
    kdx = 1.0/ (nx_2 * dx)
    kdy = 1.0/ (ny_2 * dy)
    nsys = 8
    systems = np.zeros(nsys, dtype=np.int64)
    for i in range(p.n):
        sys_idx = m.isys[i] -1
        if 0 <= sys_idx < nsys:
            systems[sys_idx] = 1

    s = np.zeros((nx, ny, nsys))
    # thermal parameters setup
    edot = p.edot_mean
    kappa = 30.0
    edot = edot *1000.0
    kappa = kappa *1000000.0
    pec = edot / (2.0* kappa)
    
    # loop through systems
    for sys in range(nsys):
        if systems[sys] == 0:
            s[:, :, sys] = 0.0
            continue
        a = a_ffted.copy()
        # validation for age parameters to prevent numerical exceptions
        if (m.ages[sys, 4] == 0 or np.isnan(m.ages[sys, 3]) or np.isnan(m.ages[sys, 4])):
            print(f"Warning: Invalid age parameters for system {sys}")
            s[:, :, sys] = 0.0
            continue
        depth = m.ages[sys, 1] *1000.0
        # add 1e-10 to avoid ZeroDivisionError
        A_o = (m.ages[sys, 3] - 6) / max(m.ages[sys, 4], 1e-10)
        # apply filter in frequency domain
        a = wave(a, size, factor, ny_2, nx_2, kdy, kdx, pec, A_o, depth)
        # inverse 2D FFT back to spatial domain
        with objmode(a='complex64[:,:]'):
            a = np.fft.ifft2(a)*(size*size)
        
        # extract filtered topography, real part
        s[:, :, sys] = np.real(a[nx1-1:nx1-1+nx, ny1-1:ny1-1+ny])

    # recalculate grid spacing in degrees for interpolation
    dx = lon[nx//2, ny//2] - lon[nx//2 -1, ny//2]
    dy = lat[nx//2, ny//2] - lat[nx//2, ny//2 -1]

    # compute the effective perturbation at the points where there are ages
    for i in range(p.n):
        i1 = int((m.x[i] - xlon) / dx) -1
        if i1 == nx -1:
            i1 = nx -2
        j1 = int((m.y[i] - xlat) / dy) -1
        if j1 == ny -1:
            j1 = ny -2
        j1 = ny -1 - j1
        # find appropriate grid indices
        for j in range(nx):
            if lon[j, 0] > m.x[i]:
                i1 = j-1
                if i1 == nx:
                    i1 = nx -1
                break
        for j in range(ny):
            if lat[0, j] > m.y[i]:
                j1 = j -1
                if j1 == ny:
                    j1 = ny -1
                break
        # bounds checking
        if j1 >= ny:
            print(f"too big {j1}, {m.y[i]}, {np.min(lat)}, {np.max(lat)}")
            raise ValueError("Index out of bounds")
        elif j1 < 0:
            print(f"too small {j1}, {m.y[i]}, {np.min(lat)}, {np.max(lat)}")
            raise ValueError("Index out of bounds")
        # nomalized coordinates for interpolation
        u = (m.x[i] - lon[i1, 0]) / (lon[i1 +1, 0] - lon[i1, 0])
        t = (m.y[i] - lat[0,j1+1]) / (lat[0, j1] - lat[0, j1+1])
        idx = m.isys[i] -1
        # delegate to separate bilinear interpolation function
        m.zc, m.depth1 = bilinear(u, t, m.zc, m.depth1, s, elev, m.elev, idx, i, i1, j1)
    return
