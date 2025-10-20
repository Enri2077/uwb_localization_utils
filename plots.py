#!/usr/bin/python3

from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
# plt.rcParams["figure.figsize"] = (10, 5)
# plt.rcParams["figure.dpi"] = 250

import pandas as pd
import numpy as np
import math
from os import path
import os
pd.options.mode.chained_assignment = None

dpi = 250

def plot_trajectory(a_x, a_y, a_label, a_color, b_x, b_y, b_label, b_color, title, plot_output_path, a_scatter=False, b_scatter=False, marker_size=0.5):
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_xticks(np.arange(-10, 101, 5), minor=False)
    ax.set_yticks(np.arange(-10, 101, 5), minor=False)
    ax.set_xticks(np.arange(-10, 101, 1), minor=True)
    ax.set_yticks(np.arange(-10, 101, 1), minor=True)
    ax.set_xlim(-1, 26)
    ax.set_ylim(-1, 9)
    ax.set_aspect('equal')
    ax.minorticks_on()
    ax.grid(which='major', color=(0.5, 0.5, 0.5), linestyle='-')
    ax.grid(which='minor', color=(0.9, 0.9, 0.9), linestyle='-')
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")

    ax.set_axisbelow(True)

    if a_scatter:
        ax.plot(a_x, a_y, '-o', ms=marker_size, linewidth=0.5, color=a_color, label=a_label)
    else:
        ax.plot(a_x, a_y, linewidth=2.0, color=a_color, label=a_label)
    if b_scatter:
        ax.plot(b_x, b_y, '-o', ms=marker_size, linewidth=0.5, color=b_color, label=b_label)
    else:
        ax.plot(b_x, b_y, linewidth=2.0, color=b_color, label=b_label)

    ax.legend()
    fig.savefig(path.join(plot_output_path, f"trajectory_{title.replace(' ', '_')}.png"), dpi=dpi)
    fig.savefig(path.join(plot_output_path, f"trajectory_{title.replace(' ', '_')}.svg"))
    # plt.close(fig)

def plot_error_xy(t, a_x, a_y, b_x, b_y, x_color, y_color, title, plot_output_path):
    # --- x y error plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("error [m]")
    ax.plot(t - t.min(), a_x - b_x, color=x_color, label='x error', linewidth=1.0)
    ax.plot(t - t.min(), a_y - b_y, color=y_color, label='y error', linewidth=1.0)
    ax.legend()
    fig.savefig(path.join(plot_output_path, f"x_y_error_{title.replace(' ', '_')}.png"), dpi=dpi)
    fig.savefig(path.join(plot_output_path, f"x_y_error_{title.replace(' ', '_')}.svg"))
    # plt.close(fig)

def plot_error(t, a_x, a_y, b_x, b_y, color, title, plot_output_path):
    # --- x y error plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("error [m]")
    ax.plot(t - t.min(), np.sqrt((a_x - b_x)**2 + (a_y - b_y)**2), color=color, label='error', linewidth=1.0)
    ax.legend()
    fig.savefig(path.join(plot_output_path, f"error_{title.replace(' ', '_')}.png"), dpi=dpi)
    fig.savefig(path.join(plot_output_path, f"error_{title.replace(' ', '_')}.svg"))
    # plt.close(fig)

def get_plot_error(title):
    # --- x y error plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("error [m]")
    return fig, ax

def plot_quality(d, title, color, plot_output_path):
    # --- Quality plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_ylim(0, 100)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("quality factor [%]")
    ax.plot(d.t - d.t.min(), d.q, color=color, label='quality factor', linewidth=1.0)
    ax.legend()
    fig.savefig(path.join(plot_output_path, f"quality_{title.replace(' ', '_')}.png"), dpi=dpi)
    fig.savefig(path.join(plot_output_path, f"quality_{title.replace(' ', '_')}.svg"))
    # plt.close(fig)
