#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
File: /workspace/code/pendulum_motion/test2.py
Project: /workspace/code/pendulum_motion
Created Date: Friday May 31st 2024
Author: Kaixu Chen
-----
Comment:
这里我们不需要考虑摆动中的能量损失，也就是说，摆动的幅度不会逐渐减小。

Have a good code time :)
-----
Last Modified: Friday June 7th 2024 12:56:34 pm
Modified By: the developer formerly known as Kaixu Chen at <chenkaixusan@gmail.com>
-----
Copyright (c) 2024 The University of Tsukuba
-----
HISTORY:
Date      	By	Comments
----------	---	---------------------------------------------------------

14-06-2024	Kaixu Chen	optimised code

12-06-2024	Kaixu Chen	Now categorise by symmetric/asymmetric, for the asymmetric case we need to consider a bias, i.e. the amplitude of the oscillations is not perfectly symmetric.
"""

import numpy as np
import matplotlib.pyplot as plt
import cv2, os, json
import itertools
import multiprocessing
import hydra
from pathlib import Path


def asymmetry_one_cycle(max_left_theta, max_right_theta, L, dt, bias: int = 0):

    x_list = []
    y_list = []
    L = 1
    # left to right
    left_degree = max_left_theta
    while left_degree > 0:
        theta = np.radians(left_degree)
        x_list.append(-L * np.sin(theta))
        y_list.append(-L * np.cos(theta))
        left_degree -= dt

    right_degree = 0
    while right_degree < max_right_theta:
        theta = np.radians(right_degree)
        x_list.append(L * np.sin(theta))
        y_list.append(-L * np.cos(theta))
        right_degree += dt

    # right to left
    while right_degree > 0:
        theta = np.radians(right_degree)
        x_list.append(L * np.sin(theta))
        y_list.append(-L * np.cos(theta))
        right_degree -= dt

    left_degree = 0
    while left_degree < max_left_theta - bias:
        theta = np.radians(left_degree)
        x_list.append(-L * np.sin(theta))
        y_list.append(-L * np.cos(theta))
        left_degree += dt

    return x_list, y_list


def save_index(x_list, file_path):

    left_index = x_list.index(min(x_list))
    right_index = x_list.index(max(x_list))

    json_info = {
        "frames": len(x_list),
        "left_index": left_index,
        "right_index": right_index,
    }

    with open(file_path, "w") as f:
        json.dump(json_info, f, indent=4)


def save_mp4(
    frames, shape_instance, shape_path, x_list, y_list, background: str = "black"
):

    # 创建动画
    fig, ax = plt.subplots()
    plt.axis("off")

    # fig setting
    fig.set_size_inches(5.2, 5.2)

    # ax setting
    ax.set_aspect("equal")
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)

    transparent_flag = False
    if background == "black":
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")
    elif background == "white":
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
    elif background == "none":
        transparent_flag = True

    (line,) = ax.plot([], [], lw=5)
    line.set_data([], [])

    ax.add_patch(shape_instance)

    width, height = fig.get_size_inches() * fig.get_dpi()
    out = cv2.VideoWriter(
        shape_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        30,
        (int(width - 120), int(height - 120)),
    )

    shape = shape_path.split("_")[-2]
    symmetry_flag = shape_path.split("/")[-4]
    left_right = shape_path.split("/")[-2]

    for i in range(int(frames)):

        x = x_list[i]
        y = y_list[i]

        # 根据摆的位置更新图形
        line.set_data([0, x], [0, y])

        # 感觉这边gap有问题
        if "circle" in shape:
            shape_instance.set_center([x, y])
        elif "rect" in shape:
            shape_instance.set_xy([x, y])

        fig.canvas.draw()

        # 先把plt的图片写入到内存，然后用cv2读出来保存成视频。我找不到什么好的转化方法了
        temp_save_path = os.path.join(
            "/workspace", f"{symmetry_flag}_{shape}_{left_right}_temp.png"
        )
        fig.savefig(
            temp_save_path,
            bbox_inches="tight",
            pad_inches=0,
            transparent=transparent_flag,
        )
        image = cv2.imread(temp_save_path)

        # image = np.frombuffer(fig.canvas.tostring_rgb(), dtype='uint8')
        # image = image.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        # image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        out.write(image)

    out.release()
    plt.close(fig)
    print(f"save {shape_path} done!")


def process_one_sample(
    left_degree,
    right_degree,
    L,
    dt,
    shape_value,
    shape_path,
    shape_index_path,
    background: str = "black",
    asymmetry_degree: int = 0,
):

    # 一次单摆运动
    # 按照4个象限来分别的话，从左到右的摆动和从右到左的摆动
    # 角度的变化是角边小，变大，半个周期结束，再变小，再变大，一个周期结束。
    x_list, y_list = asymmetry_one_cycle(
        left_degree, right_degree, L, dt, asymmetry_degree
    )

    total_degree = (
        left_degree + right_degree + left_degree + right_degree - asymmetry_degree
    )
    frames = total_degree / dt

    save_mp4(frames, shape_value, shape_path, x_list, y_list, background)
    save_index(x_list, shape_index_path)


def random_shape(degree_boundary: list):

    # 配置形状，从三个形状里面选择一个
    # 一个形状里面，大小不同，以及在轴上的大小不同

    # 随机生成形状，以及配置
    # circle
    random_radius = np.linspace(0.1, 0.5, 10)
    random_stick_length = np.linspace(0.5, 1, 10)

    circle_list = list(itertools.product(random_radius, random_stick_length))
    np.random.shuffle(circle_list)

    circle_split_index = int(0.2 * len(circle_list))

    # rect
    random_height = np.linspace(0.1, 0.5, 5)
    random_width = np.linspace(0.1, 0.5, 5)
    rect_list = list(
        itertools.product(random_height, random_width, random_stick_length)
    )
    np.random.shuffle(rect_list)

    shape_info = {"circle": circle_list, "rect": rect_list}

    # 对称的角度
    degree = list(itertools.product(degree_boundary, degree_boundary))
    # 非对称的角度
    # degree = [(i, j) for i, j in itertools.product(degree_boundary, repeat=2) if i == j]
    return shape_info, degree


def main(params, shape: str, infos: list, deg, asymmetry_flag: int = 0):

    # 设置单摆的参数
    # g = 9.81  # 重力加速度 (m/s^2)
    dt = params.dt  # 时间步长
    res_config = []
    left_degree, right_degree = deg

    print(f"left_degree: {left_degree}, right_degree: {right_degree}")
    print(f"asymmetry_degree: {asymmetry_flag}")

    background = params.background
    root_path = params.save_root_path

    save_path = (
        Path(root_path.replace("pendulum", f"pendulum_{background}_{dt}")) / "raw/data"
    )
    save_index_path = (
        Path(root_path.replace("pendulum", f"pendulum_{background}_{dt}"))
        / "raw/index_mapping"
    )
    config_save_path = (
        Path(root_path.replace("pendulum", f"pendulum_{background}_{dt}")) / "config"
    )

    # 保存动画到文件
    # 保存index，作为融合的索引
    path = os.path.join(
        f"{save_path}",
        f"assymmetry_degree{asymmetry_flag}",
        shape,
        f"left{left_degree}_right{right_degree}",
    )
    index_path = os.path.join(
        f"{save_index_path}", f"assymmetry_degree{asymmetry_flag}", shape
    )

    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    if not os.path.exists(index_path):
        os.makedirs(index_path, exist_ok=True)

    if shape == "circle":

        for idx, info in enumerate(infos):
            print(f"shape: {shape}, info: {info}")
            shape_instance = plt.Circle((0, 0), info[0], fc="r")  # 使用圆形表示摆的端点
            l = info[1]

            # 保存圆形的配置
            config = {
                "left_degree": left_degree,
                "right_degree": right_degree,
                "radius": info[0],
                "l": l,
            }
            res_config.append(config)

            shape_path = os.path.join(
                path, f"left{left_degree}_right{right_degree}_{shape}_{idx}.mp4"
            )
            shape_index_path = os.path.join(
                index_path, f"left{left_degree}_right{right_degree}_{shape}_{idx}.json"
            )

            process_one_sample(
                left_degree,
                right_degree,
                l,
                dt,
                shape_instance,
                shape_path,
                shape_index_path,
                background,
                asymmetry_flag,
            )

    elif shape == "rect":

        for idx, info in enumerate(infos):
            print(f"shape: {shape}, info: {info}")

            width = info[0]
            height = info[1]
            shape_instance = plt.Rectangle((0, 0), width, height, fc="r")
            l = info[2]

            config = {
                "left_degree": left_degree,
                "right_degree": right_degree,
                "width": width,
                "height": height,
                "l": l,
            }
            res_config.append(config)

            shape_path = os.path.join(
                path, f"left{left_degree}_right{right_degree}_{shape}_{idx}.mp4"
            )
            shape_index_path = os.path.join(
                index_path, f"left{left_degree}_right{right_degree}_{shape}_{idx}.json"
            )

            process_one_sample(
                left_degree,
                right_degree,
                l,
                dt,
                shape_instance,
                shape_path,
                shape_index_path,
                background,
                asymmetry_flag,
            )

    # save config
    config_path = os.path.join(f"{config_save_path}")
    if not os.path.exists(config_path):
        os.makedirs(config_path, exist_ok=True)

    with open(
        os.path.join(
            config_path, f"left{left_degree}_right{right_degree}_{shape}_config.json"
        ),
        "w",
    ) as f:
        json.dump(res_config, f, indent=4)


@hydra.main(config_path="/workspace/code/configs", config_name="generate_dataset.yaml")
def init_params(config):

    threads = []

    random_index, degree = random_shape(config.degree_boundary)

    # * 这里为了处理多线程，加快生成速度
    for shape, shape_info in random_index.items():
        for deg in degree:
            for i in config.asymmetry_degree:
                # main(config, shape, shape_info, deg, i) # ! only for test

                multi_process = multiprocessing.Process(
                    target=main, args=(config, shape, shape_info, deg, i)
                )
                threads.append(multi_process)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    print(f"Total {len(threads)} threads!")
    # finish file check
    print("*" * 50)
    root_path = config.save_root_path
    save_path = (
        Path(root_path.replace("pendulum", f"pendulum_{config.background}_{config.dt}"))
        / "raw/data"
    )
    data_list = list(save_path.glob("**/*.mp4"))
    print(f"Total {len(data_list)} files generated!")
    # shape check
    for shape in save_path.iterdir():
        print(f"shape: {shape.name}, total: {len(list(shape.glob('**/*.mp4')))}")
    print("*" * 50)


if "__main__" == __name__:

    init_params()
