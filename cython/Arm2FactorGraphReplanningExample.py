import gtsam
from gpmp2 import gpmp2
import numpy as np

import util
import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import argparse


def plan(plot=False, plot_interpolation=False):
    dataset = util.Dataset2D.get('OneObstacleDataset')
    origin_point2 = gtsam.Point2(dataset.origin_x, dataset.origin_y)

    # Signed distance field
    field = dataset.SDF()
    sdf = gpmp2.PlanarSDF(origin_point2, dataset.cell_size, field)
    arm = util.generate_arm('SimpleTwoLinksArm')

    start_conf = np.array([0, 0])
    start_vel = np.array([0, 0])

    end_conf = np.array([math.pi / 2, 0])
    end_vel = np.array([0, 0])

    replan_pose_index = 5
    replan_end_conf = np.array([math.pi / 2 + 0.4, -math.pi / 4])

    total_time_sec = 5.0
    total_time_step = 10
    total_check_step = 50

    delta_t = total_time_sec / total_time_step

    # The number of time steps to interpolate for obstacle avoidance
    check_inter = total_check_step / total_time_step - 1

    # GP
    Qc = np.identity(2)
    Qc_model = gtsam.noiseModel_Gaussian.Covariance(Qc)

    # Obstacle avoidance settings
    cost_sigma = 0.1
    epsilon_dist = 0.1

    # Noise model
    pose_fix_sigma = 0.0001
    vel_fix_sigma = 0.0001

    # Optimizer settings
    optimizer_settings = gpmp2.TrajOptimizerSetting(2)
    optimizer_settings.set_total_step(total_time_step)
    optimizer_settings.set_total_time(total_time_sec)
    optimizer_settings.set_epsilon(epsilon_dist)
    optimizer_settings.set_cost_sigma(cost_sigma)
    optimizer_settings.set_obs_check_inter(check_inter)
    optimizer_settings.set_conf_prior_model(pose_fix_sigma)
    optimizer_settings.set_vel_prior_model(vel_fix_sigma)
    optimizer_settings.set_Qc_model(Qc)

    init_values = gpmp2.initArmTrajStraightLine(
        start_conf,
        end_conf,
        total_time_step,
    )
    original_trajectory_values = gpmp2.BatchTrajOptimize2DArm(
        arm,
        sdf,
        start_conf,
        start_vel,
        end_conf,
        end_vel,
        init_values,
        optimizer_settings,
    )
    print('Done, but no validation on whether it\'s right')

    # ISAM initialization
    isam_planner = gpmp2.ISAM2TrajOptimizer2DArm(arm, sdf, optimizer_settings)
    isam_planner.initFactorGraph(start_conf, start_vel, end_conf, end_vel)
    isam_planner.initValues(original_trajectory_values)

    # One update lets ISAM accept the original values
    isam_planner.update()

    # Now we begin the replanning phase
    # First, fix current conf and vel
    current_conf = original_trajectory_values.atVector(
        util.symbol('x', replan_pose_index)
    )
    current_vel = original_trajectory_values.atVector(
        util.symbol('v', replan_pose_index)
    )
    isam_planner.fixConfigAndVel(replan_pose_index, current_conf, current_vel)

    # Update replanned end conf and (unchanged) end vel
    isam_planner.changeGoalConfigAndVel(replan_end_conf, end_vel)

    # Optimize
    isam_planner.update()

    replanned_trajectory_values = isam_planner.values()
    print(replanned_trajectory_values)

    if not plot and not plot_interpolation:
        print('Done!')
        return

    if plot and plot_interpolation:
        # Because of programmer laziness, I only plot interpolated paths or not
        print(
            'Both plot and plot_interpolation set to true. '
            'Falling back to plot_interpolation.'
        )
    if plot_interpolation:
        interpolation_amount = 5
        total_plot_step = total_time_step * (interpolation_amount + 1)
        original_plot_values = gpmp2.interpolateArmTraj(
            original_trajectory_values,
            Qc_model,
            delta_t,
            interpolation_amount,
        )
        replanned_plot_values = gpmp2.interpolateArmTraj(
            replanned_trajectory_values,
            Qc_model,
            delta_t,
            interpolation_amount,
        )
    else:
        interpolation_amount = 0
        total_plot_step = total_time_step
        original_plot_values = original_trajectory_values
        replanned_plot_values = replanned_trajectory_values

    # TODO update this to be more detailed
    dataset.get_sdf_plot(field)
    print('Plotting?')

    # Plot start / end config
    dataset.get_evidence_map_plot()
    util.get_planar_arm_plot(arm.fk_model(), start_conf, 'blue', 2)
    util.get_planar_arm_plot(arm.fk_model(), end_conf, 'red', 2)
    util.get_planar_arm_plot(arm.fk_model(), replan_end_conf, 'coral', 2)

    # The animation function is more custom, so I just put it here
    fig, ax = dataset.get_evidence_map_plot()
    original_confs = [
        original_plot_values.atVector(gtsam.symbol(ord('x'), i))
        for i in range(total_plot_step)
    ]

    fk = arm.fk_model()
    original_positions = []
    for c in original_confs:
        p = fk.forwardKinematicsPosition(c)[0:2, :]
        position = np.zeros((p.shape[0], p.shape[1] + 1))
        position[:, 1:] = p
        original_positions.append(position)

    replanned_confs = [
        replanned_plot_values.atVector(gtsam.symbol(ord('x'), i))
        for i in range(total_plot_step)
    ]

    fk = arm.fk_model()
    replanned_positions = []
    for c in replanned_confs:
        p = fk.forwardKinematicsPosition(c)[0:2, :]
        position = np.zeros((p.shape[0], p.shape[1] + 1))
        position[:, 1:] = p
        replanned_positions.append(position)

    original_line, = ax.plot(
        original_positions[0][0, :],
        original_positions[0][1, :],
        color='blue',
        linewidth=2
    )

    replanned_line, = ax.plot(
        replanned_positions[0][0, :],
        replanned_positions[0][1, :],
        color='skyblue',
        linewidth=2
    )

    def animate(i):
        original_line.set_xdata(original_positions[i][0, :])
        original_line.set_ydata(original_positions[i][1, :])
        replanned_line.set_xdata(replanned_positions[i][0, :])
        replanned_line.set_ydata(replanned_positions[i][1, :])

    # # For some reason, this needs to be assigned or else the
    # animation does not work
    anim = animation.FuncAnimation(
        fig,
        animate,
        interval=100,
        frames=total_plot_step,
    )
    plt.legend((original_line, replanned_line), ('Original', 'Replanned'))

    plt.draw()
    plt.show()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Optimize and then replan for a simple 2D dataset'
    )
    parser.add_argument('--plot', action='store_true')
    parser.add_argument('--plot_interpolation', action='store_true')
    args = parser.parse_args()
    plan(args.plot, args.plot_interpolation)