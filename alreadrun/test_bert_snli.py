"""
Train the ESIM model on the preprocessed SNLI dataset.
"""
# Aurelien Coet, 2018.

from utils.runned.utils_test_three import validate
from vaa.model_transformer import ESIM
# from vaa.model_bert_transformer import ESIM
import os
import argparse
import json
import numpy as np
import pickle
import torch
import matplotlib
matplotlib.use('Agg')


def transform_batch_data(data, batch_size=64, shuffle=True):
    data_batch = dict()
    data_batch['premises'] = dict()
    data_batch['hypotheses'] = dict()
    data_batch['labels'] = dict()
    index = np.arange(len(data['labels']))
    if shuffle:
        np.random.shuffle(index)

    idx = -1
    for i in range(len(index)):
        if i % batch_size == 0:
            idx += 1
            data_batch['premises'][idx] = []
            data_batch['hypotheses'][idx] = []
            data_batch['labels'][idx] = []
        data_batch['premises'][idx].append(data['premises'][index[i]])
        data_batch['hypotheses'][idx].append(data['hypotheses'][index[i]])
        data_batch['labels'][idx].append(int(data['labels'][index[i]]))
    return data_batch


def main(train_file,
         valid_file,
         test_file,
         target_dir,
         embedding_size=512,
         hidden_size=512,
         dropout=0.5,
         num_classes=3,
         epochs=64,
         batch_size=32,
         lr=0.0004,
         patience=5,
         max_grad_norm=10.0,
         checkpoint=None):
    """
    Train the ESIM model on the Quora dataset.

    Args:
        train_file: A path to some preprocessed data that must be used
            to train the model.
        valid_file: A path to some preprocessed data that must be used
            to validate the model.
        embeddings_file: A path to some preprocessed word embeddings that
            must be used to initialise the model.
        target_dir: The path to a directory where the trained model must
            be saved.
        hidden_size: The size of the hidden layers in the model. Defaults
            to 300.
        dropout: The dropout rate to use in the model. Defaults to 0.5.
        num_classes: The number of classes in the output of the model.
            Defaults to 3.
        epochs: The maximum number of epochs for training. Defaults to 64.
        batch_size: The size of the batches for training. Defaults to 32.
        lr: The learning rate for the optimizer. Defaults to 0.0004.
        patience: The patience to use for early stopping. Defaults to 5.
        checkpoint: A checkpoint from which to continue training. If None,
            training starts from scratch. Defaults to None.
    """
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    print(20 * "=", " Preparing for training ", 20 * "=")

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # -------------------- Data loading ------------------- #
    print("\t* Loading training data...")
    with open(train_file, "rb") as pkl:
        train_data = pickle.load(pkl)

    print("\t* Loading validation data...")
    with open(valid_file, "rb") as pkl:
        valid_data = pickle.load(pkl)
        valid_dataloader = transform_batch_data(valid_data, batch_size=batch_size, shuffle=False)

    print("\t* Loading test data...")
    with open(test_file, "rb") as pkl:
        test_data = pickle.load(pkl)
        test_dataloader = transform_batch_data(test_data, batch_size=batch_size, shuffle=False)

    # -------------------- Model definition ------------------- #
    print("\t* Building model...")

    model = ESIM(embedding_size,
                 hidden_size,
                 dropout=dropout,
                 num_classes=num_classes,
                 device=device).to(device)

    # -------------------- Preparation for training  ------------------- #

    # Continuing training from a checkpoint if one was given as argument.
    if checkpoint:
        checkpoint = torch.load(checkpoint)
        start_epoch = checkpoint["epoch"] + 1

        print("\t* Training will continue on existing model from epoch {}..."
              .format(start_epoch))

        model.load_state_dict(checkpoint["model"])

    # Compute loss and accuracy before starting (or resuming) training.
    _, valid_accuracy = validate(model, valid_dataloader)
    print("\t* Validation accuracy: {:.4f}%".format(valid_accuracy*100))

    # _, test_loss, test_accuracy = validate(model,
    #                                          test_dataloader,
    #                                          criterion)
    # print("\t* test loss before training: {:.4f}, accuracy: {:.4f}%"
    #       .format(test_loss, (test_accuracy*100)))



if __name__ == "__main__":
    default_config = "../../config/training/snli_training_bert.json"

    parser = argparse.ArgumentParser(
        description="Train the ESIM model on quora")
    parser.add_argument("--config",
                        default=default_config,
                        help="Path to a json configuration file")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    script_dir = script_dir + '/scripts/training'

    parser.add_argument("--checkpoint",
                        default=os.path.dirname(os.path.realpath(__file__)) + '/data/checkpoints/SNLI/bert/' +"best.pth.tar",
                        help="Path to a checkpoint file to resume training")
    args = parser.parse_args()

    if args.config == default_config:
        config_path = os.path.join(script_dir, args.config)
    else:
        config_path = args.config

    with open(os.path.normpath(config_path), 'r') as config_file:
        config = json.load(config_file)

    main(os.path.normpath(os.path.join(script_dir, config["train_data"])),
         os.path.normpath(os.path.join(script_dir, config["valid_data"])),
         os.path.normpath(os.path.join(script_dir, config["test_data"])),
         os.path.normpath(os.path.join(script_dir, config["target_dir"])),
         config["embedding_size"],
         config["hidden_size"],
         0, # dropout
         config["num_classes"],
         config["epochs"],
         32, # batch_size
         config["lr"],
         config["patience"],
         config["max_gradient_norm"],
         args.checkpoint)
