"""Design calculator for a circular-waveguide ("can") antenna.

    python cantenna_design.py                 # 5.2 GHz, 41 mm can (this project)
    python cantenna_design.py --f 2.44 --d 83 # e.g. a 2.4 GHz design

Theory (circular waveguide of inner diameter D, fed by a quarter-wave probe):
* Cut-off of mode TE_nm : f_c = x'_nm * c / (pi * D);  TM_nm : x_nm instead.
  The can must carry only the dominant TE11 mode:
      f_c(TE11) = 1.8412 c/(pi D)  <  f  <  f_c(TM01) = 2.4048 c/(pi D)
* Guided wavelength  lambda_g = lambda_0 / sqrt(1 - (f_c/f)^2)
* Probe height  = lambda_0 / 4,   probe-to-back-wall distance = lambda_g / 4
  (the short circuit reflects in phase at the probe),
  can length >= 3 lambda_g / 4.
* Aperture gain estimate  G = e_ap (pi D / lambda_0)^2, with e_ap ~ 0.84 for
  the TE11 field distribution of an open circular waveguide.
"""

import argparse
import math
import os

C0 = 299_792_458.0
X11_PRIME = 1.8412      # first root of J1'  -> TE11
X01 = 2.4048            # first root of J0   -> TM01
APERTURE_EFFICIENCY_TE11 = 0.84


def design(f_hz, d_m):
    lam0 = C0 / f_hz
    fc_te11 = X11_PRIME * C0 / (math.pi * d_m)
    fc_tm01 = X01 * C0 / (math.pi * d_m)
    if not fc_te11 < f_hz < fc_tm01:
        raise ValueError(f"{f_hz / 1e9:.2f} GHz is outside the single-mode band "
                         f"{fc_te11 / 1e9:.2f}-{fc_tm01 / 1e9:.2f} GHz for D = {d_m * 1e3:.1f} mm")
    lam_g = lam0 / math.sqrt(1 - (fc_te11 / f_hz) ** 2)
    gain = APERTURE_EFFICIENCY_TE11 * (math.pi * d_m / lam0) ** 2
    return dict(lambda0_mm=lam0 * 1e3, lambda_g_mm=lam_g * 1e3,
                fc_te11_mhz=fc_te11 / 1e6, fc_tm01_mhz=fc_tm01 / 1e6,
                probe_height_mm=lam0 / 4 * 1e3, probe_to_back_mm=lam_g / 4 * 1e3,
                min_length_mm=0.75 * lam_g * 1e3, gain_estimate_dbi=10 * math.log10(gain))


def plot_design_window(f_hz, d_m, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    f = np.linspace(2.0e9, 6.5e9, 400)
    d_min = X11_PRIME * C0 / (math.pi * f) * 1e3
    d_max = X01 * C0 / (math.pi * f) * 1e3
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))

    ax = axs[0]
    ax.fill_between(f / 1e9, d_min, d_max, alpha=0.25, label="single-mode TE11 region")
    ax.plot(f / 1e9, d_min, "C0", lw=1)
    ax.plot(f / 1e9, d_max, "C0", lw=1)
    for lo, hi, name in ((2.40, 2.4835, "2.4 GHz Wi-Fi"), (5.15, 5.85, "5 GHz Wi-Fi")):
        ax.axvspan(lo, hi, color="grey", alpha=0.15)
        ax.text((lo + hi) / 2, 125, name, ha="center", fontsize=8)
    ax.plot(f_hz / 1e9, d_m * 1e3, "r*", ms=14, label=f"this design ({d_m * 1e3:.0f} mm @ {f_hz / 1e9:.1f} GHz)")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Can inner diameter (mm)")
    ax.set_ylim(20, 135)
    ax.set_title("Which can sizes work at which frequency")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=8)

    ax = axs[1]
    d = np.linspace(X11_PRIME * C0 / (math.pi * f_hz) * 1.02, X01 * C0 / (math.pi * f_hz) * 0.999, 300)
    lam0 = C0 / f_hz
    lam_g = lam0 / np.sqrt(1 - (X11_PRIME * C0 / (math.pi * d) / f_hz) ** 2)
    ax.plot(d * 1e3, lam_g / 4 * 1e3, label="probe-to-back distance  λg/4")
    ax.plot(d * 1e3, 0.75 * lam_g * 1e3, label="minimum can length  3λg/4")
    r = design(f_hz, d_m)
    ax.plot([d_m * 1e3] * 2, [r["probe_to_back_mm"], r["min_length_mm"]], "r*", ms=12)
    ax.set_xlabel("Can inner diameter (mm)")
    ax.set_ylabel("mm")
    ax.set_ylim(0, 250)
    ax.set_title(f"Dimensions at {f_hz / 1e9:.1f} GHz (small cans get long quickly)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--f", type=float, default=5.2, help="frequency in GHz")
    parser.add_argument("--d", type=float, default=41.0, help="can inner diameter in mm")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    try:
        r = design(args.f * 1e9, args.d / 1e3)
    except ValueError as err:
        raise SystemExit(f"error: {err}")
    print(f"Cantenna for {args.f:.3f} GHz, D = {args.d:.1f} mm")
    for k, v in r.items():
        print(f"  {k:20s} {v:9.2f}")
    if not args.no_plot:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "design_window.png")
        plot_design_window(args.f * 1e9, args.d / 1e3, out)
        print(f"figure written to {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
