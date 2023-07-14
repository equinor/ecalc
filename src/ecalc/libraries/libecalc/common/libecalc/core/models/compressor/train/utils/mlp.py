# Utils
import json
import time

# For visualization of results
from pathlib import Path

import numpy as np
import pandas as pd

# Torch imports
import torch
from torch import Tensor, nn
from torch.optim import Adam
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader, Dataset


def dump_json(obj, path):
    """
    Creating a json object holding the results of output.
    """

    with open(path, "w", encoding="utf8") as fout:
        json.dump(obj, fout, indent=4, ensure_ascii=False)


def load_json(path):
    """
    Load results to find the loss of dev data.
    """

    with open(path, encoding="utf8") as fin:
        return json.load(fin)


class MyDataset(Dataset):
    """
    This class takes data from gen_data.csv and create tensor data out of it.
    It also normalizes the data (both input and output).
    """

    def __init__(self, type_of_training_data):
        df = pd.DataFrame()
        try:
            df = pd.read_csv("src/physical_modelling/reconditioned_data/gen_data.csv")
        except FileNotFoundError:
            print(
                "File not found. Create data from data_generator.ipynb first. Remember to create the required amount noted in the code."
            )
            exit()
        print("data size: " + str(df.shape[0]))

        # Scales the correspoding column in the data to normalize it
        # Remember to change the output plot as well when changing the scaling here
        # TODO Create better normalization algorithms for the data
        df["pressure_2"] = df["pressure_2"].apply(lambda x: x * (1 / 400))
        df["enthalpy_2"] = df["enthalpy_2"].apply(lambda x: x * (1 / 300000))

        # Handle eos
        # print(df['eos'])
        # eos_list = ["SRK", "PR", "GERG_SRK", "GERG_PR"]
        # eos_df = pd.DataFrame(columns=eos_list)

        # print('=== Start ===')
        # print(eos_df)
        # for eos in df['eos']:
        #     row = [0, 0, 0, 0]
        #     for i in range(len(eos_list)):
        #         if eos.upper() == eos_list[i]:
        #             row[i] = 1
        #     eos_df.loc[len(eos_df)] = row
        # for i in eos_df.iterrows():
        #     print(i)
        # print('=== end ===')

        # Defining the size of the 3 stacks of data
        self.type_of_training_data = type_of_training_data
        self.train_data_size = 100000
        self.dev_data_size = 20000
        self.test_data_size = 20000

        # Stops the program if not enough data for the 3 stacks
        if self.train_data_size + self.dev_data_size + self.test_data_size > df.shape[0]:
            print("Not enough data for the training size, add more data or change the training size")
            exit()

        # Separate the data into 3 stacks
        self.data_frame = pd.DataFrame()
        if type_of_training_data == "train":
            self.data_frame = df.iloc[: self.train_data_size]
            print(self.data_frame)
        elif type_of_training_data == "dev":
            self.data_frame = df.iloc[self.train_data_size : (self.train_data_size + self.dev_data_size)]
            # TODO for each row in dataframe select index and change it to it minus traindatasize
            self.data_frame.index = np.arange(0, len(self.data_frame))
            print(self.data_frame)
        elif type_of_training_data == "test":
            self.data_frame = df.iloc[
                (self.train_data_size + self.dev_data_size) : (
                    self.train_data_size + self.dev_data_size + self.test_data_size
                )
            ]
            self.data_frame.index = np.arange(0, len(self.data_frame))
            print(self.data_frame)

        # Input data
        self.data = torch.stack(
            [
                torch.tensor(self.data_frame["pressure_2"], dtype=torch.float32),
                torch.tensor(self.data_frame["enthalpy_2"], dtype=torch.float32),
                torch.tensor(self.data_frame["water"], dtype=torch.float32),
                torch.tensor(self.data_frame["nitrogen"], dtype=torch.float32),
                torch.tensor(self.data_frame["CO2"], dtype=torch.float32),
                torch.tensor(self.data_frame["methane"], dtype=torch.float32),
                torch.tensor(self.data_frame["ethane"], dtype=torch.float32),
                torch.tensor(self.data_frame["propane"], dtype=torch.float32),
                torch.tensor(self.data_frame["i-butane"], dtype=torch.float32),
                torch.tensor(self.data_frame["n-butane"], dtype=torch.float32),
                torch.tensor(self.data_frame["i-pentane"], dtype=torch.float32),
                torch.tensor(self.data_frame["n-pentane"], dtype=torch.float32),
                torch.tensor(self.data_frame["n-hexane"], dtype=torch.float32),
                # torch.tensor(self.data_frame["SRK"], dtype=torch.float32),
                # torch.tensor(self.data_frame["PR"], dtype=torch.float32),
                # torch.tensor(self.data_frame["GERG_SRK"], dtype=torch.float32),
                # torch.tensor(self.data_frame["GERG_PR"], dtype=torch.float32),
            ],
            dim=1,
        )

        # Output data
        self.label = torch.stack(
            [
                torch.tensor(self.data_frame["z_2"], dtype=torch.float32),
                torch.tensor(self.data_frame["k_2"], dtype=torch.float32),
                # torch.tensor(self.data_frame["density_2"], dtype=torch.float32),
            ],
            dim=1,
        )

    def __getitem__(self, index: int) -> tuple:
        return self.data[index], self.label[index]

    def __len__(self) -> int:
        return self.data_frame.shape[0]


class Mlp(nn.Module):
    """
    This is main class for the neural network model.
    It takes in an input dim and a list of hidden dims and generates a neural network.
    """

    def __init__(self, input_dim: int, hidden_dims: list[int]):
        """
        Output dim is the last dim in `hidden_dims`.
        """

        super().__init__()
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims

        # self.ln = nn.LayerNorm(input_dim) # Didn't get better result from it

        # Creating layers out of hidden dims
        layers = []
        cur_dim = input_dim
        for i in range(len(hidden_dims) - 1):
            layers.append(nn.Linear(cur_dim, hidden_dims[i]))
            layers.append(nn.GELU())
            cur_dim = hidden_dims[i]
        # No activation after last layer
        layers.append(nn.Linear(cur_dim, hidden_dims[-1]))
        self.layers = nn.Sequential(*layers)

    def forward(self, x: Tensor):
        """
        Returns an output after passing the input through the model.
        """

        # x: (b, input_dim)
        # x = self.ln(x)
        x = self.layers(x)
        return x


def evaluate(
    model: Mlp,
    data: MyDataset,
    device: str,
    ckpt_dir: Path,
    batch_size: int = 64,
) -> dict:
    """
    Evaluate an epoch to see how it performed.
    It generates a checkpoint for the epoch in result/mlp which holds the loss changes and output comparisons.
    """

    model.eval()  # Change to eval mode
    loader = DataLoader(data, batch_size=batch_size, shuffle=False)
    losses = []
    all_preds = []
    all_labels = []

    print("==== Evaluation ====")
    loss_fn = nn.MSELoss()  # Remember to change the loss function in main train method too if you want to change this
    with torch.inference_mode():  # Turn off gradient computations
        for _step, batch in enumerate(loader):
            # batch: tuple of (inputs, labels)
            inputs = batch[0].to(device)
            labels = batch[1].to(device)

            # Forward
            preds = model(inputs)
            loss = loss_fn(preds, labels)

            losses.append(loss.item())
            all_preds.append(preds)
            all_labels.append(labels)
    avg_loss = sum(losses) / len(losses)
    print(f"Avg loss: {avg_loss}")
    print(f"Max loss: {max(losses)}")

    # Convert all_preds and all_labels
    # [(b, output_dim), (b, output_dim), ...] -> (n, output_dim)
    all_preds = torch.cat(all_preds, dim=0)
    all_preds = all_preds.cpu().tolist()  # Turn into list of lists
    all_labels = torch.cat(all_labels, dim=0)
    all_labels = all_labels.cpu().tolist()  # Turn into list of lists

    return {
        "loss": avg_loss,
        "preds": all_preds,
        "labels": all_labels,
    }


def train(
    model: Mlp,
    output_dir: Path,
    train_data: MyDataset,
    dev_data: MyDataset,
    num_epochs: int,
    optimizer: Adam,  # Change this when changing the optimizer object
    lr_scheduler: StepLR,
    device: str,
    batch_size: int = 64,
    log_interval: int = 500,
):
    """
    This is the main training loop.
    batch_size can be changed depending on RAM size.
    """

    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    start_time = time.time()
    model.train()  # Change to training mode

    print("\n ==== Start training! ====")
    print(f"Device: {device}")
    print(f"Start time: {start_time}")
    print(f"# epochs: {num_epochs}")
    print(f"# train examples: {len(train_data)}")
    print(f"# batches: {len(train_loader)}")
    print(f"Batch size: {batch_size} \n")

    loss_fn = nn.MSELoss()  # Remember to change the loss function in evaluate() too
    epoch_losses = []
    for epoch in range(num_epochs):
        batch_losses = []
        print("Epoch", epoch)
        for step, batch in enumerate(train_loader):
            # batch: tuple of (inputs, labels)

            # Move to GPU if available
            inputs = batch[0].to(device)  # (b, input_dim)
            labels = batch[1].to(device)  # (b, output_dim)

            # Forward
            output = model(inputs)

            # Backward
            loss = loss_fn(output, labels)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

            # Log info every `log_interval` steps
            if step % log_interval == 0:
                log_info = {
                    "Epoch": epoch,
                    "Step": step,
                    "Loss": loss.item(),
                    "Learning rate": lr_scheduler.get_last_lr()[0],
                    "Time(sec)": time.time() - start_time,
                }
                print(log_info)

            batch_losses.append(loss.item())

        # Update learning rate
        lr_scheduler.step()

        avg_loss = sum(batch_losses) / len(train_loader)
        epoch_losses.append(avg_loss)

        # print(f"End of epoch {epoch}")
        print(f"Average train loss: {avg_loss}")

        # Save checkpoint to a checkpoint directory
        ckpt_dir = output_dir / f"ckpt-{epoch}"
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        # Evaluate and save the results
        eval_result = evaluate(model, dev_data, device, ckpt_dir)
        dump_json(eval_result, ckpt_dir / "result.json")
        dump_json(batch_losses, ckpt_dir / "train_loss.json")
        torch.save(model.state_dict(), ckpt_dir / "model.pt")

    print(f"Total time used: {time.time()-start_time}\n")
    print("==== Training finished! ====")


def load_model(model: Mlp, path_to_model: Path):
    """
    Load model to cpu for use.
    """

    state_dict = torch.load(path_to_model, map_location="cpu")
    model.load_state_dict(state_dict)


def load_best_ckpt(model: Mlp, output_dir: Path, final_dir: Path):
    """
    Find the checkpoint by dev loss.
    """

    ckpt_dirs = [d for d in output_dir.glob("ckpt-*") if d.is_dir()]
    if len(ckpt_dirs) < 1:
        print("No checkpoints found!")
    best_ckpt_dir = None
    best_dev_loss = float("inf")
    for ckpt_dir in ckpt_dirs:
        dev_result = load_json(ckpt_dir / "result.json")
        dev_loss: float = dev_result["loss"]
        if dev_loss < best_dev_loss:
            best_dev_loss = dev_loss
            best_ckpt_dir = ckpt_dir
    if best_ckpt_dir is not None:
        print(f"Best dev loss: {best_dev_loss}")
        ckpt_path = best_ckpt_dir / "model.pt"
        print(f"Loading model from {ckpt_path}")
        # Load the checkpoint back to cpu, so we can start evaluate
        load_model(model, ckpt_path)
        # state_dict = torch.load(ckpt_path, map_location="cpu")
        # model.load_state_dict(state_dict)
        # Save model to final_model
        final_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), final_dir / "model.pt")


def initiate_model(input_dim: int, device: str):
    # Hyperparameters
    # hidden_dims = [1024, 1024, 1024, 1024, 1024, 1024, 512, 64, 16, 3]
    # hidden_dims = [256, 256, 256, 256, 256, 32, 3]
    # hidden_dims = [128, 128, 128, 128, 128, 128, 128, 128, 128, 32, 3]
    # hidden_dims = [128, 128, 32, 3]
    # hidden_dims = [64, 64, 64, 64, 64, 16, 3]
    # hidden_dims = [256, 256, 256, 256, 3]
    # hidden_dims = [1024, 1024, 128, 3]
    # hidden_dims = [512, 512, 3]
    hidden_dims = [256, 256, 256, 256, 3]
    # hidden_dims = [128, 128, 3]
    # hidden_dims = [64, 64, 3]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Mlp(input_dim, hidden_dims)
    model = model.to(device)  # move to GPU if available
    return model


def initiate_train():
    """
    This is the main train function.
    """

    print("Loading data and model...")
    # Hyperparameters
    # hidden_dims = [1024, 1024, 1024, 1024, 1024, 1024, 512, 64, 16, 3]
    # hidden_dims = [256, 256, 256, 256, 256, 32, 3]
    # hidden_dims = [128, 128, 128, 128, 128, 128, 128, 128, 128, 32, 3]
    # hidden_dims = [128, 128, 32, 3]
    # hidden_dims = [64, 64, 64, 64, 64, 16, 3]
    # hidden_dims = [256, 256, 256, 256, 3]
    # hidden_dims = [1024, 1024, 128, 3]
    # hidden_dims = [512, 512, 3]
    # hidden_dims = [256, 256, 3]
    # hidden_dims = [128, 128, 3]
    # hidden_dims = [64, 64, 3]

    # Initial learning rate
    lr = 0.005

    # Setting up Data
    torch.manual_seed(0)  # Set random seed for reproducibility
    train_data = MyDataset("train")
    print(train_data.data)
    dev_data = MyDataset("dev")
    print(dev_data.data)
    test_data = MyDataset("test")
    print(test_data.data)
    # input_dim = train_data[0][0].shape[0]  # get input dim from data

    # Model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # model = Mlp(input_dim, hidden_dims)
    # model = model.to(device)  # move to GPU if available
    model = initiate_model(train_data[0][0].shape[0], device)

    optimizer = Adam(model.parameters(), lr=lr)
    lr_scheduler = StepLR(optimizer, step_size=2, gamma=0.95)
    num_epochs = 4

    output_dir = Path("result/mlp")
    final_dir = Path("src/machine_learning/final_model")

    train(
        model,
        output_dir=output_dir,
        train_data=train_data,
        dev_data=dev_data,
        num_epochs=num_epochs,
        optimizer=optimizer,
        lr_scheduler=lr_scheduler,
        device=device,
    )
    load_best_ckpt(model, output_dir, final_dir)
    evaluate(model, test_data, device, output_dir)


def main():
    initiate_train()
    # execute([12, 13, 45, 34, 0.5, 85, 454, 4, 545, 45, 4545, 45, 45, 12, 1, 1, 1], "src/machine_learning/final_model/model.pt")


def execute(input: list[float], final_dir: Path):
    """
    Take in a list of inputs and runs through the trained model.
    Returns 3 outputs.
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = initiate_model(len(input), device)
    load_model(model, final_dir)
    print("sds")
    return 0


def predict():
    return 0


if __name__ == "__main__":
    main()
