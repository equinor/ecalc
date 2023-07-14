import copy
from pathlib import Path

import mlp
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


class NeuralNet:
    def __init__(self, init_path: Path):
        self.hidden_dims = [256, 256, 256, 256, 2]
        self.mlp = mlp.Mlp(input_dim=13, hidden_dims=self.hidden_dims)
        mlp.load_model(self.mlp, init_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def predict(self, dataframe):
        # self.mlp.eval()
        data = FeatureData(dataframe)
        loader = DataLoader(data, batch_size=1, shuffle=False)

        all_preds = []
        with torch.inference_mode():
            for _step, batch in enumerate(loader):
                inputs = batch[0].to(self.device)

                preds = self.mlp(inputs)

                all_preds.append(preds)

        if len(all_preds) <= 1:
            array = np.array(all_preds[0])
            outlet_z = array[0]
            outlet_kappa = array[1]
        else:
            outlet_z = []
            outlet_kappa = []
            for eachTensor in all_preds:
                # eachPred = eachTensor.tolist()
                outlet_z.append(eachTensor[0])
                outlet_kappa.append(eachTensor[1])

        return np.array(outlet_z), np.array(outlet_kappa)


class FeatureData(Dataset):
    def __init__(self, df: pd.DataFrame):
        self.df = copy.deepcopy(df)
        self.df["pressure_2"] = self.df["pressure_2"].apply(lambda x: x * (1 / 400))
        self.df["enthalpy_2"] = self.df["enthalpy_2"].apply(lambda x: x * (1 / 300000))

        # Input data
        self.data = torch.stack(
            [
                torch.tensor(self.df["pressure_2"], dtype=torch.float32),
                torch.tensor(self.df["enthalpy_2"], dtype=torch.float32),
                torch.tensor(self.df["water"], dtype=torch.float32),
                torch.tensor(self.df["nitrogen"], dtype=torch.float32),
                torch.tensor(self.df["CO2"], dtype=torch.float32),
                torch.tensor(self.df["methane"], dtype=torch.float32),
                torch.tensor(self.df["ethane"], dtype=torch.float32),
                torch.tensor(self.df["propane"], dtype=torch.float32),
                torch.tensor(self.df["i_butane"], dtype=torch.float32),
                torch.tensor(self.df["n_butane"], dtype=torch.float32),
                torch.tensor(self.df["i_pentane"], dtype=torch.float32),
                torch.tensor(self.df["n_pentane"], dtype=torch.float32),
                torch.tensor(self.df["n_hexane"], dtype=torch.float32),
            ],
            dim=1,
        )

    def __getitem__(self, index: int) -> tuple:
        return self.data[index]

    def __len__(self) -> int:
        return self.df.shape[0]


def main():
    features = [
        "pressure_2",
        "enthalpy_2",
        "water",
        "nitrogen",
        "CO2",
        "methane",
        "ethane",
        "propane",
        "i_butane",
        "n_butane",
        "i_pentane",
        "n_pentane",
        "n_hexane",
    ]

    df = pd.read_csv("src/physical_modelling/reconditioned_data/gen_data.csv")[features]
    path = Path("src/machine_learning/final_model/model.pt")
    nn = NeuralNet(path)

    result = nn.predict(df)
    print(result)


if __name__ == "__main__":
    main()
