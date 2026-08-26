'''
Visualization utilities for Fine Timing Suite sequences
=======================================================================
Lightweight plotting functions for pulse sequence results.
'''

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from scipy.optimize import curve_fit


class Visualizer:
    """
    Minimal visualization utilities for Fine Timing Suite pulse sequences.
    """
    TEXT_BBOX_STYLE = dict(
        boxstyle="round",
        facecolor="white",
        edgecolor="gray",
        linewidth=0.8,
        alpha=0.8
    )

    CONTRAST_MODES = {
        "signal_over_ss": "Signal / Steady State",
        "signal_over_off": "Signal / MW Off",
        "signal_minus_off": "(Signal - MW Off) / MW Off",
    }

    DATA_TRACES = {
        "MW On - Signal": "signal1_cts_s",
        "MW Off - Signal": "signal2_cts_s",
        "MW On - Steady State": "reference1_cts_s",
        "MW Off - Steady State": "reference2_cts_s",
    }

    @staticmethod
    def plot_experiment(data, spec, cfg=None, fit=True, view="raw"):
        # ---------------------------
        # 1. X axis
        # ---------------------------
        x = getattr(data, spec["x_key"])

        # ---------------------------
        # 2. Build traces
        # ---------------------------
        traces = {}

        for label, attr in spec["traces"].items():
            if hasattr(data, attr):
                traces[label] = getattr(data, attr)
            else:
                print(f"[WARN] Missing trace: {attr} ({label}) — skipping")

        # ---------------------------
        # 3. Derived data (optional)
        # ---------------------------
        contrast_mode = spec.get("contrast_mode", None)

        contrast = None
        if contrast_mode is not None:
            contrast = Visualizer._compute_contrast(traces, contrast_mode)

        # ---------------------------
        # 4. Plot raw data
        # ---------------------------
        plt.figure(figsize=(8, 5))

        if view == "raw":
            for label, y in traces.items():
                plt.plot(x, y, '.', label=label, alpha=0.5)

        elif view == "contrast":
            if contrast is None:
                raise ValueError("Contrast requested but not defined for this experiment.")
            plt.plot(x, contrast, '.', label=Visualizer.CONTRAST_MODES.get(contrast_mode, None), alpha=0.7)

        else:
            raise ValueError(f"Unknown view: {view}")

        # ---------------------------
        # 5. Fit
        # ---------------------------
        fit_params = None

        if fit and "fit" in spec:

            fit_cfg = spec["fit"]

            # override trace depending on view
            if view == "contrast":
                y = contrast
            else:
                trace_name = fit_cfg["trace"]

                if trace_name not in traces:
                    raise ValueError(
                        f"Fit trace '{trace_name}' missing. Available: {list(traces.keys())}"
                    )

                y = traces[trace_name]

            try:
                popt, _ = curve_fit(
                    fit_cfg["model"],
                    x,
                    y,
                    p0=fit_cfg["initial_guess"](x, y),
                    maxfev=10000
                )

                fit_params = popt

                x_fit = np.linspace(np.min(x), np.max(x), 1000)
                y_fit = fit_cfg["model"](x_fit, *popt)

                plt.plot(x_fit, y_fit, '-', label=f"{fit_cfg['label']} fit")

            except RuntimeError:
                print("Fit failed.")

        # ---------------------------
        # 6. Labels
        # ---------------------------
        plt.xlabel(spec.get("x_label", "x"))
        plt.ylabel(spec.get("y_label", "Counts/s" if view == "raw" else Visualizer.CONTRAST_MODES.get(contrast_mode, None)))
        plt.title(spec.get("name", "Experiment"))

        # ---------------------------
        # 7. Annotation block
        # ---------------------------
        text_lines = []

        # config annotations (shared)
        if cfg is not None:
            if hasattr(cfg, "mw_freq"):
                text_lines.append(f"MW freq: {cfg.mw_freq/1e9:.3f} GHz")
            if hasattr(cfg, "mw_gain"):
                text_lines.append(f"MW gain: {cfg.mw_gain}")

        # experiment-specific annotations
        if fit_params is not None and "fit" in spec:
            text_lines += spec["fit"]["format_params"](fit_params)
            fit_equation = spec["fit"].get("equation")
            if fit_equation:
                text_lines.append(f"Model: {fit_equation}")

        if "annotations" in spec:
            text_lines += spec["annotations"](cfg, fit_params)

        if text_lines:
            plt.text(
                0.02, 0.98,
                "\n".join(text_lines),
                transform=plt.gca().transAxes,
                va='top',
                fontsize=10,
                bbox=Visualizer.TEXT_BBOX_STYLE # dict(boxstyle="round", alpha=0.6)
            )

        plt.legend(loc="lower right")
        plt.tight_layout()
        plt.show()


    @staticmethod
    def _compute_contrast(traces, mode):
        if "MW On - Signal" not in traces:
            raise ValueError("Contrast requires 'MW On - Signal' trace but it is missing.")

        signal = traces["MW On - Signal"]

        if mode == "signal_over_ss":
            if "MW On - Steady State" not in traces:
                raise ValueError("Contrast mode 'Signal / Steady State' requires 'MW On - Steady State' trace.")
            return signal / traces["MW On - Steady State"]

        elif mode == "signal_over_off":
            if "MW Off - Signal" not in traces:
                raise ValueError("Contrast mode 'Signal / MW Off' requires 'MW Off - Signal' trace.")
            return signal / traces["MW Off - Signal"]

        elif mode == "signal_minus_off":
            if "MW Off - Signal" not in traces:
                raise ValueError("Contrast mode 'Signal - MW Off' requires 'MW Off - Signal' trace.")
            return (signal - traces["MW Off - Signal"]) / traces["MW Off - Signal"]

        else:
            raise ValueError(f"Unknown contrast mode: {mode}")
        

    @staticmethod
    def plot_podmr(data, cfg=None, fit=True, contrast_mode="signal_over_off", view="raw"):
        """Plot PODMR (pulsed ODMR) data with optional Laplace dip fit.
        
        Parameters
        ----------
            data : object
                Data object containing signal1/signal1_cts_s, signal2/signal2_cts_s, and mw_fMHz.
            cfg : object, optional
                Configuration object with attributes like mw_freq, mw_gain, etc.
            fit : bool, default True
                Whether to fit a Laplace dip model to the ratio.
            contrast_mode : str, default "signal_over_off"
                Method for computing contrast if view="contrast". 
                Options: "signal_over_ss": "Signal / Steady State", "signal_over_off": "Signal / MW Off", "signal_minus_off": "Signal - MW Off".
            view : str, default "raw"
                Plotting view mode passed to plot_experiment.
        """
        def lorentzian_dip_model(x, depth, mu, b, C):
            return C - depth / (1 + ((x - mu) / b) ** 2)
        # TODO: Add a triplet dip model fow when there is observable hyperfine splitting

        def initial_guess(x, y):
            span = float(np.max(x) - np.min(x))
            y_min = float(np.min(y))
            C0 = float(np.median(y))
            depth0 = max(C0 - y_min, 1e-4)
            b0 = max(span / 20.0, 1e-6)
            return [depth0, np.mean(x), b0, C0]

        def format_params(p):
            depth, mu, b, C = p
            return [
                f"d = {depth:.4f}",
                f"$\\mu$ = {mu:.3f} MHz",
                f"b (HWHM) = {b:.3f} MHz",
                f"C = {C:.3f}",
            ]

        PODMR_SPEC = {
            "name": "PODMR",
            "x_key": "mw_fMHz",
            "x_label": "Frequency (MHz)",
            "contrast_mode": contrast_mode,
            "traces": Visualizer.DATA_TRACES,
            "fit": {
                "model": lorentzian_dip_model,
                "trace": "MW On - Signal",
                "initial_guess": initial_guess,
                "format_params": format_params,
                "label": "Lorentzian Dip",
                "equation": r"$y = C - \frac{d}{1 + ((x-\mu)/b)^2}$",
            }
        }

        Visualizer.plot_experiment(data, PODMR_SPEC, cfg=cfg, fit=fit, view=view)


    @staticmethod
    def plot_rabi(data, cfg=None, fit=True, contrast_mode="signal_over_off", view="raw"):
        """Plot Rabi oscillation data with optional fit and contrast views.
        
        Parameters
        ----------
            data : object
                Data object containing the necessary attributes for plotting.
            cfg : object, optional
                    Configuration object with attributes like mw_freq, mw_gain, etc. Used for annotations.
            fit : bool, default True
                    Whether to perform a fit to the Rabi oscillation.
            contrast_mode : str, default "signal_over_off"
                    Method for computing contrast if view="contrast". 
                    Options: "signal_over_ss": "Signal / Steady State", "signal_over_off": "Signal / MW Off", "signal_minus_off": "Signal - MW Off".
            view : str, default "raw"
                    Whether to plot raw traces or contrast. Options: "raw", "contrast".
        """

        def rabi_initial_guess(x, y):
            A0 = (np.max(y) - np.min(y)) / 2
            C0 = np.mean(y)
            T0 = 1.0 / np.fft.rfftfreq(len(x), d=max(float(np.median(np.diff(x))), 1e-12))[1 + np.argmax(np.abs(np.fft.rfft(y - np.mean(y)))[1:])]
            tau0 = 100
            return [A0, T0, C0, tau0]


        def format_rabi_params(p):
            A, T, C, tau = p
            freq = 1 / T if T != 0 else 0

            return [
                f"A = {A:.2f}",
                rf"$\pi$-pulse = {T/2:.2f} ns",
                f"f = {freq*1e3:.2f} MHz",
                f"$\\tau$ = {tau:.2f} ns",
                f"C = {C:.2f}",
            ]


        def decaying_cos(x, A, T, C, tau):
            return A * np.cos(x * 2 * np.pi / T) * np.exp(-x / tau) + C


        RABI_SPEC = {
            "name": "Rabi Oscillation",
            "x_key": "mw_duration_ftns",
            "x_label": "MW Duration (ns)",
            "contrast_mode": contrast_mode,
            "traces": Visualizer.DATA_TRACES,
            "fit": {
                "model": decaying_cos,
                "trace": "MW On - Signal",
                "initial_guess": rabi_initial_guess,
                "format_params": format_rabi_params,
                "label": "Rabi",
                "equation": r"$y = A \cos(2\pi fx) e^{-x/\tau} + C$",
            }
        }

        Visualizer.plot_experiment(data, RABI_SPEC, cfg=cfg, fit=fit, view=view)


    @staticmethod
    def plot_cpmg(data, cfg=None, contrast_mode="signal_over_ss", view="raw"):
        CPMG_SPEC = {
            "name": "CPMG-XY",
            "x_key": "tau_ftns",
            "x_label": rf"$\tau$ (ns)",
            "contrast_mode": contrast_mode,
            "traces": Visualizer.DATA_TRACES,
        }

        Visualizer.plot_experiment(data, CPMG_SPEC, cfg=cfg, fit=False, view=view)


    @staticmethod
    def plot_hahnecho(data, cfg=None, contrast_mode="signal_over_off", fit=True, view="raw"):
        # NOTE: This is configured for a pi/2 Y - tau - pi X - tau - pi/2 -Y Hahn Echo sequence.
        def dephasing_model(x, A, t2star, C):
            return A * np.exp(-x / t2star) + C

        def initial_guess(x, y):
            span = float(np.max(x) - np.min(x))
            y_min = float(np.min(y))
            y_max = float(np.max(y))
            C0 = y_min
            A0 = max(y_max - C0, 1e-4)
            t2star0 = max(span / 10.0, 1e-6)
            return [A0, t2star0, C0]

        def format_params(p):
            A, t2star, C = p
            return [
                f"A = {A:.4f}",
                f"$T_2^*$ = {t2star:.3f} $\\mu$s",
                f"C = {C:.3f}",
            ]

        HAHNECHO_SPEC = {
            "name": "Hahn Echo",
            "x_key": "tau_ftus",
            "x_label": f"$\\tau$ ($\\mu$s)",
            "contrast_mode": contrast_mode,
            "traces": Visualizer.DATA_TRACES,
            "fit": {
                "model": dephasing_model,
                "trace": "MW On - Signal",
                "initial_guess": initial_guess,
                "format_params": format_params,
                "label": "Hahn Echo Decay",
                "equation": r"$y = A e^{-x/T_2^*} + C$",
            }
        }

        Visualizer.plot_experiment(data, HAHNECHO_SPEC, cfg=cfg, fit=fit, view=view)

    @staticmethod
    def plot_ramsey(data, cfg=None, contrast_mode="signal_over_off", fit=True, view="raw", fit_mode="oscillatory"):
        # NOTE: This is configured for a pi/2 Y - tau - pi/2 -Y Ramsey sequence.
        def ramsey_model(x, A, f, t2star, C):
            return A * np.exp(-x / t2star) * np.cos(2 * np.pi * f * x) + C
            # TODO: Implement model capable of handling the 3 frequency components under hyperfine splitting

        def decay_model(x, A, t2star, C):
            return A * np.exp(-x / t2star) + C

        def ramsey_initial_guess(x, y):
            span = max(float(np.max(x) - np.min(x)), 1e-6)
            dx = max(float(np.median(np.diff(x))) if len(x) > 1 else span, 1e-12)
            y0 = y - np.mean(y)
            freqs = np.fft.rfftfreq(len(y0), d=dx)
            spectrum = np.abs(np.fft.rfft(y0))
            f0 = float(freqs[1 + np.argmax(spectrum[1:])]) if len(spectrum) > 1 else 1.0 / span
            return [0.5 * (np.max(y) - np.min(y)), max(f0, 1e-9), max(span, 1e-6), np.mean(y)]

        def decay_initial_guess(x, y):
            span = max(float(np.max(x) - np.min(x)), 1e-6)
            return [max(y[0] - y[-1], 1e-4), max(span, 1e-6), y[-1]]

        def ramsey_format_params(p):
            A, f, t2star, C = p
            return [
                f"A = {A:.4f}",
                f"f = {f*1e3:.3f} MHz",
                f"$T_2^*$ = {t2star:.3f} ns",
                f"C = {C:.3f}",
            ]

        def decay_format_params(p):
            A, t2star, C = p
            return [
                f"A = {A:.4f}",
                f"$T_2^*$ = {t2star:.3f} ns",
                f"C = {C:.3f}",
            ]

        fit_mode = str(fit_mode).lower()

        if fit_mode == "decay":
            fit_cfg = {
                "model": decay_model,
                "trace": "MW On - Signal",
                "initial_guess": decay_initial_guess,
                "format_params": decay_format_params,
                "label": "Ramsey Decay",
                "equation": r"$y = A e^{-x/T_2^*} + C$",
            }
        elif fit_mode == "oscillatory":
            fit_cfg = {
                "model": ramsey_model,
                "trace": "MW On - Signal",
                "initial_guess": ramsey_initial_guess,
                "format_params": ramsey_format_params,
                "label": "Ramsey Oscillatory",
                "equation": r"$y = A e^{-x/T_2^*}\cos(2\pi f x) + C$",
            }
        else:
            raise ValueError(f"Unknown Ramsey fit mode: {fit_mode}")

        RAMSEY_SPEC = {
            "name": "Ramsey",
            "x_key": "tau_ftns",
            "x_label": rf"$\tau$ (ns)",
            "contrast_mode": contrast_mode,
            "traces": Visualizer.DATA_TRACES,
            "fit": fit_cfg,
        }

        Visualizer.plot_experiment(data, RAMSEY_SPEC, cfg=cfg, fit=fit, view=view)


    @staticmethod
    def plot_t1(data, cfg=None, fit=True, contrast_mode="signal_minus_off", view="raw"):
        # NOTE: This is configured for an inversion recovery T1 sequence with pi - tau - readout.
        def t1_model(x, A, t1, C):
            return A * np.exp(-x / t1) + C

        def initial_guess(x, y):
            span = max(float(np.max(x) - np.min(x)), 1e-6)
            return [max(y[0] - y[-1], 1e-4), max(span, 1e-6), y[-1]]

        def format_params(p):
            A, t1, C = p
            return [
                f"A = {A:.4f}",
                f"$T_1$ = {t1/1e3:.3f} $\\mu$s",
                f"C = {C:.3f}",
            ]

        T1_SPEC = {
            "name": "T1 Relaxation",
            "x_key": "delay_tus",
            "x_label": f"Delay ($\\mu$s)",
            "contrast_mode": contrast_mode,
            "traces": Visualizer.DATA_TRACES,
            "fit": {
                "model": t1_model,
                "trace": "MW On - Signal",
                "initial_guess": initial_guess,
                "format_params": format_params,
                "label": "T1 Fit",
                "equation": r"$y = A e^{-x/T_1} + C$",
            }
        }

        Visualizer.plot_experiment(data, T1_SPEC, cfg=cfg, fit=fit, view=view)