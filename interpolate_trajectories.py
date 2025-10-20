#!/usr/bin/python3

import numpy as np
import pandas as pd

def interpolate_pose_2d_trajectories(trajectory_a_df, trajectory_b_df, trajectory_a_label, trajectory_b_label, interpolation_tolerance=0.2):
    a = trajectory_a_label
    b = trajectory_b_label

    trajectory_a_df['T'] = pd.to_datetime(trajectory_a_df.t, unit='s')
    trajectory_b_df['T'] = pd.to_datetime(trajectory_b_df.t, unit='s')

    tolerance = pd.Timedelta('{}s'.format(interpolation_tolerance))

    # interpolate trajectory_b around trajectory_a timestamps
    forward_matches = pd.merge_asof(
        left=trajectory_a_df[['T', 't', 'x', 'y']],
        right=trajectory_b_df[['T', 't', 'x', 'y']],
        on='T',
        direction='forward',
        tolerance=tolerance,
        suffixes=(f'_{a}', f'_{b}'))

    backward_matches = pd.merge_asof(
        left=trajectory_a_df[['T', 't', 'x', 'y']],
        right=trajectory_b_df[['T', 't', 'x', 'y']],
        on='T',
        direction='backward',
        tolerance=tolerance,
        suffixes=(f'_{a}', f'_{b}'))

    forward_backward_matches = pd.merge(
        left=backward_matches,
        right=forward_matches,
        on=f't_{a}')

    interpolated_trajectory_b_list = list()
    for index, row in forward_backward_matches.iterrows():
        t_b_1, t_b_2 = row[f't_{b}_x'], row[f't_{b}_y']
        t_int = row[f't_{a}']

        # if the trajectory_a time is too far from a trajectory_b time (before or after), do not use this trajectory_a data point
        if pd.isnull(t_b_1) or pd.isnull(t_b_2):
            continue

        x_a = row[f'x_{a}_x']
        x_b_1, x_b_2 = row[f'x_{b}_x'], row[f'x_{b}_y']
        x_int = np.interp(t_int, [t_b_1, t_b_2], [x_b_1, x_b_2])

        y_a = row[f'y_{a}_x']
        y_b_1, y_b_2 = row[f'y_{b}_x'], row[f'y_{b}_y']
        y_int = np.interp(t_int, [t_b_1, t_b_2], [y_b_1, y_b_2])

        interpolated_trajectory_b_list.append({
            't': t_int,
            f'x_{a}': x_a,
            f'y_{a}': y_a,
            f'x_{b}': x_int,
            f'y_{b}': y_int,
        })

    return pd.DataFrame(interpolated_trajectory_b_list)

def interpolate_pose_2d_trajectory(timestamps_df, trajectory_b_df, trajectory_b_label, interpolation_tolerance=0.2):
    a = 'timestamps'
    b = trajectory_b_label

    timestamps_df['T'] = pd.to_datetime(timestamps_df.t, unit='s')
    trajectory_b_df['T'] = pd.to_datetime(trajectory_b_df.t, unit='s')

    tolerance = pd.Timedelta('{}s'.format(interpolation_tolerance))

    # interpolate trajectory_b around timestamps_df
    forward_matches = pd.merge_asof(
        left=timestamps_df[['T', 't']],
        right=trajectory_b_df[['T', 't', 'x', 'y']],
        on='T',
        direction='forward',
        tolerance=tolerance,
        suffixes=(f'_{a}', f'_{b}'))

    backward_matches = pd.merge_asof(
        left=timestamps_df[['T', 't']],
        right=trajectory_b_df[['T', 't', 'x', 'y']],
        on='T',
        direction='backward',
        tolerance=tolerance,
        suffixes=(f'_{a}', f'_{b}'))

    forward_backward_matches = pd.merge(
        left=backward_matches,
        right=forward_matches,
        on=f't_{a}')

    interpolated_trajectory_b_list = list()
    for index, row in forward_backward_matches.iterrows():
        t_b_1, t_b_2 = row[f't_{b}_x'], row[f't_{b}_y']
        t_int = row[f't_{a}']

        # if the trajectory_a time is too far from a trajectory_b time (before or after), do not use this trajectory_a data point
        if pd.isnull(t_b_1) or pd.isnull(t_b_2):
            continue

        x_b_1, x_b_2 = row[f'x_x'], row[f'x_y']
        x_int = np.interp(t_int, [t_b_1, t_b_2], [x_b_1, x_b_2])

        y_b_1, y_b_2 = row[f'y_x'], row[f'y_y']
        y_int = np.interp(t_int, [t_b_1, t_b_2], [y_b_1, y_b_2])

        interpolated_trajectory_b_list.append({
            't': t_int,
            f'x': x_int,
            f'y': y_int,
        })

    return pd.DataFrame(interpolated_trajectory_b_list)
