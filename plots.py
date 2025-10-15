#!/usr/bin/python3

from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
# plt.rcParams["figure.figsize"] = (10, 5)

import pandas as pd
import numpy as np
import math
from os import path
import os
pd.options.mode.chained_assignment = None

def plot_trajectory(d, title, plot_output_path):
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_xlim(-1, 26)
    ax.set_ylim(-1, 9)
    ax.set_aspect('equal')
    ax.minorticks_on()
    ax.grid(which='major', color=(0.5, 0.5, 0.5), linestyle='-')
    ax.grid(which='minor', color=(0.9, 0.9, 0.9), linestyle='-')
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.xaxis.set_major_locator(MaxNLocator(steps=[5]))
    ax.yaxis.set_major_locator(MaxNLocator(steps=[5]))
    ax.plot(d.x_uwb, d.y_uwb, color='blue', label='UWB')
    ax.plot(d.x_rtk, d.y_rtk, color='red', label='RTK')
    ax.legend()
    # fig.savefig(path.join(plot_output_path, f"plot_trajectory_{title}.png"))
    fig.savefig(path.join(plot_output_path, f"plot_trajectory_{title}.svg"))
    # plt.close(fig)

def plot_error(d, title, plot_output_path):
    # --- x y error plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("x, y error [m]")
    ax.plot(d.t - d.t.min(), d.x_uwb - d.x_rtk, color='blue', label='x')
    ax.plot(d.t - d.t.min(), d.y_uwb - d.y_rtk, color='red', label='y')
    ax.legend()
    # fig.savefig(path.join(plot_output_path, f"plot_x_y_error_{title}.png"))
    fig.savefig(path.join(plot_output_path, f"plot_x_y_error_{title}.svg"))
    # plt.close(fig)

    # --- abs error plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("abs error [m]")
    ax.plot(d.t - d.t.min(), np.sqrt((d.x_uwb - d.x_rtk)**2 + (d.y_uwb - d.y_rtk)**2), color='black', label='abs error')
    ax.legend()
    # fig.savefig(path.join(plot_output_path, f"plot_abs_error_{title}.png"))
    fig.savefig(path.join(plot_output_path, f"plot_abs_error_{title}.svg"))
    # plt.close(fig)

def plot_quality(d, title, plot_output_path):
    # --- Quality plot ---
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_ylim(0, 100)
    ax.grid()
    ax.set_xlabel("t [s]")
    ax.set_ylabel("quality factor [%]")
    ax.plot(d.t - d.t.min(), d.q, color='black', label='quality factor')
    ax.legend()
    # fig.savefig(path.join(plot_output_path, f"plot_quality_{title}.png"))
    fig.savefig(path.join(plot_output_path, f"plot_quality_{title}.svg"))
    # plt.close(fig)
