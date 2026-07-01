# GLIDE

### A Python-based software for thermochronological exhumation-rate inversion

GLIDE 2.0 is a program for reconstructing spatial and temporal exhumation-rate histories from thermochronological data using a linear inversion modeling framework.

The original GLIDE algorithm was developed by Fox et al. (2014) in Fortran. Version 2.0 was rewritten in Python and further optimized by Ren et al. (2026, unpublished), providing a standalone interface and additional tools for data preparation and visualization.

## Overview

GLIDE performs linear inversions of thermochronological ages to estimate spatial and temporal exhumation rate distributions. The program integrates:

- Thermochronological datasets
- Surface topography
- Thermal parameters
- Other nacessary constraints

Model outputs include posterior exhumation-rate distributions, reduced variance, temporal resolution, and predicted thermochronological ages. Model outputs include posterior exhumation-rate distributions, reduced variance, temporal resolution, and predicted thermochronological ages. In addition, two utility Python scripts are provided for result visualization and DEM downloading as .xyz topography files.

A case study from the Shanxi Rift system (after Wang et al., 2025) is also provided, including example inputs and outputs. For using details, see Manual.pdf in the repository.

## Major References

Fox, M., Herman, F., Willett, S.D., May, D.A., 2014. A linear inversion method to infer exhumation rates in space and time from thermochronometric data. Earth Surface Dynamics, 2, 47–65. https://doi.org/10.5194/esurf-2-47-2014

Willett, S.D., Herman, F., Fox, M., et al., 2021. Bias and error in modelling thermochronometric data. Earth Surface Dynamics, 9, 1153–1221. https://doi.org/10.5194/esurf-9-1153-2021

Ren, G.S., Han, X., Dai, J.G., Yu, Z.C., Fox, M.., 2026. A Python-based optimization of the linear inversion method for thermochronological exhumation rates. Submitted to Computers & Geosciences.

## Citation

If you use GLIDE 2.0 in scientific research, please cite the following references:

- Fox et al. (2014)
- Willett et al. (2021)
- Ren et al. (2026)

## Disclaimer

GLIDE is intended for scientific and educational applications in thermochronological inverse modeling. Users should carefully evaluate geological assumptions, data quality, and thermal model parameters before interpreting inversion results.
