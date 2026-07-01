def write_output(m, p):
    """
    Write output files for visualizing results
    matrices: object containing various matrices
    params: object containing parameters
    """
    # Pre-calculate frequently used values
    m_max = p.m_max
    dummy = p.dummy
    method = ["AFT", "ZFT", "AHe", "ZHe",
              "HAr", "MAr", "BAr", "KAr"]
    file_syn = open(f"{p.run}/Predicted ages.csv", "w")
    file_syn.write("longitude,latitude,observed age,observed std,"
                   "predicted age,method\n")
    for i in range(p.n):
        file_syn.write(f"{m.x[i]},{m.y[i]},{m.ta[i]},{m.a_error[i]},"
                       f"{m.syn_age[i]},{method[m.isys[i]-1]}\n")

    for j in range(1, m_max + 1):
        rest = sum(m.tsteps[:m_max - j + 1])
        rest2 = sum(m.tsteps[:m_max - j]) if m_max - j > 0 else 0.0
        itime = round(rest * 10)
        cs = f"{itime:04d}"

        file_o = open(f"{p.run}/{cs}.csv", "w", newline="")
        file_o.write(
            "longitude,latitude,exhumation rate,reduced variance,time resolution\n"
        )

        file_o2 = open(f"{p.run}/{cs}.txt", "w")
        # Write header information
        lon1 = p.lon1 + 360 if p.lon1 < 0 else p.lon1
        file_o2.write(
            f"{lon1:6.2f}{p.lat2:6.2f}0 20 0 1 BL {rest:8.2f} -{rest2:8.2f} Ma\n"
        )
        # Write data points
        for i in range(1, dummy + 1):
            idx = j + (i - 1) * m_max
            # Write to main file
            x = m.x_dum_true[i - 1]
            y = m.y_dum_true[i - 1]
            edot_val = m.edot[idx - 1]
            eps_dum_val = m.eps_dum[idx - 1]
            sf_val = m.sf[idx - 1]
            uncertainty_val = eps_dum_val * eps_dum_val / p.sigma2
            file_o.write(
                f"{float(x)},{float(y)},{float(edot_val)},{float(uncertainty_val)},{float(sf_val)}\n"
            )
            # Write to uncertainty file
            #file_k1.write(f"{float(x)} {float(y)} {float(uncertainty_val)} {float(sf_val)}\n")
        # Close files if they were opened in this iteration
        file_o.close()
        file_o2.close()
    return
