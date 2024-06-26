#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
File: /workspace/code/project/main.py
Project: /workspace/code/project
Created Date: Sunday June 2nd 2024
Author: Kaixu Chen
-----
Comment:

Have a good code time :)
-----
Last Modified: Sunday June 2nd 2024 2:05:10 pm
Modified By: the developer formerly known as Kaixu Chen at <chenkaixusan@gmail.com>
-----
Copyright (c) 2024 The University of Tsukuba
-----
HISTORY:
Date      	By	Comments
----------	---	---------------------------------------------------------
'''

import os, logging

from pytorch_lightning import Trainer, seed_everything
from pytorch_lightning.loggers import TensorBoardLogger

# callbacks
from pytorch_lightning.callbacks import (
    TQDMProgressBar,
    RichModelSummary,
    ModelCheckpoint,
    EarlyStopping,
    LearningRateMonitor,
)

from dataloader.data_loader import PendulumDataModule
from trainer.train_single import SingleModule
from trainer.train_temporal_mix import TemporalMixModule
from trainer.train_late_fusion import LateFusionModule
from cross_validation import DefineCrossValidation

import hydra

# from cross_validation import DefineCrossValidation
from helper import save_helper

def train(hparams, dataset_idx, fold):
    """the train process for the one fold.

    Args:
        hparams (hydra): the hyperparameters.
        dataset_idx (int): the dataset index for the one fold.
        fold (int): the fold index.

    Returns:
        list: best trained model, data loader
    """

    seed_everything(42, workers=True)

    if "single" in hparams.train.experiment:
        classification_module = SingleModule(hparams)
    elif hparams.train.experiment == "temporal_mix":
        classification_module = TemporalMixModule(hparams)
    elif hparams.train.experiment == "late_fusion":
        classification_module = LateFusionModule(hparams)
    else:
        raise ValueError("the experiment is not supported.")

    data_module = PendulumDataModule(hparams, dataset_idx)

    # for the tensorboard
    tb_logger = TensorBoardLogger(
        save_dir=os.path.join(hparams.train.log_path),
        name=str(fold),  # here should be str type.
    )

    # some callbacks
    progress_bar = TQDMProgressBar(refresh_rate=100)
    rich_model_summary = RichModelSummary(max_depth=2)

    # define the checkpoint becavier.
    model_check_point = ModelCheckpoint(
        filename="{epoch}-{val/loss:.2f}-{val/video_acc:.4f}",
        auto_insert_metric_name=False,
        monitor="val/video_acc",
        mode="max",
        save_last=False,
        save_top_k=2,
    )

    # define the early stop.
    early_stopping = EarlyStopping(
        monitor="val/video_acc",
        patience=2,
        mode="max",
    )

    lr_monitor = LearningRateMonitor(logging_interval="step")

    trainer = Trainer(
        devices=[
            int(hparams.train.gpu_num),
        ],
        accelerator="gpu",
        max_epochs=hparams.train.max_epochs,
        logger=tb_logger,  # wandb_logger,
        check_val_every_n_epoch=1,
        callbacks=[
            progress_bar,
            rich_model_summary,
            model_check_point,
            early_stopping,
            lr_monitor,
        ],
        fast_dev_run=hparams.train.fast_dev_run,  # if use fast dev run for debug.
    )

    trainer.fit(classification_module, data_module)

    # the validate method will wirte in the same log twice, so use the test method.
    trainer.test(
        classification_module,
        data_module,
        ckpt_path="best",
    )

    if "single" in hparams.train.experiment:
        classification_module = SingleModule.load_from_checkpoint(trainer.checkpoint_callback.best_model_path)
        # classification_module = SingleModule.load_from_checkpoint('/workspace/code/logs/single_stance/resnet/2024-06-05/9/14-16-47/fold0/version_0/checkpoints/0-2.20-0.1355.ckpt')
    elif hparams.train.experiment == "temporal_mix":
        classification_module = TemporalMixModule.load_from_checkpoint(trainer.checkpoint_callback.best_model_path)
    elif hparams.train.experiment == "late_fusion":
        classification_module = LateFusionModule.load_from_checkpoint(trainer.checkpoint_callback.best_model_path)
    else:
        raise ValueError("the experiment is not supported.")

    # save_helper(hparams, classification_module, data_module, fold) #! debug only
    save_helper(
        hparams,
        classification_module,
        data_module,
        fold,
    )

@hydra.main(
    version_base=None,
    config_path="/workspace/code/configs",
    config_name="config.yaml",
)
def init_params(config):
    #############
    # prepare dataset index
    #############

    fold_dataset_idx = DefineCrossValidation(config)()

    logging.info("#" * 50)
    logging.info("Start train all fold")
    logging.info("#" * 50)

    #############
    # K fold
    #############
    # * for one fold, we first train/val model, then save the best ckpt preds/label into .pt file.

    for fold, dataset_value in fold_dataset_idx.items():
        logging.info("#" * 50)
        logging.info("Start train fold: {}".format(fold))
        logging.info("#" * 50)

        train(config, dataset_value, fold)

        logging.info("#" * 50)
        logging.info("finish train fold: {}".format(fold))
        logging.info("#" * 50)

    logging.info("#" * 50)
    logging.info("finish train all fold")
    logging.info("#" * 50)


if __name__ == "__main__":
    os.environ["HYDRA_FULL_ERROR"] = "1"
    init_params()
