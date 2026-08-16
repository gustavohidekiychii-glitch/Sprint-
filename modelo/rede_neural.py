import numpy as np
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

from .dataset import carregar_dataset


class RiskNet(nn.Module):
    """
    Rede neural simples (Multilayer Perceptron) para
    classificação binária de risco a partir de 'horas_uso'.
    """

    def __init__(self, entrada=1, oculta=16):
        super().__init__()

        self.rede = nn.Sequential(
            nn.Linear(entrada, oculta),
            nn.ReLU(),
            nn.Linear(oculta, oculta),
            nn.ReLU(),
            nn.Linear(oculta, 1)
        )

    def forward(self, x):
        return self.rede(x)


class ModeloRisco:
    """
    Wrapper em torno da RiskNet para imitar a interface do
    sklearn (fit/predict).
    """

    def __init__(self, epocas=200, lr=0.01):
        self.epocas = epocas
        self.lr = lr
        self.scaler = StandardScaler()
        self.rede = RiskNet()

    def fit(self, X, y):

        X_np = self.scaler.fit_transform(X)
        y_np = np.array(y, dtype="float32").reshape(-1, 1)

        X_tensor = torch.tensor(X_np, dtype=torch.float32)
        y_tensor = torch.tensor(y_np, dtype=torch.float32)

        criterio = nn.BCEWithLogitsLoss()
        otimizador = torch.optim.Adam(
            self.rede.parameters(), lr=self.lr
        )

        self.rede.train()

        for _ in range(self.epocas):

            otimizador.zero_grad()

            saida = self.rede(X_tensor)
            perda = criterio(saida, y_tensor)

            perda.backward()
            otimizador.step()

        return self

    def predict_proba(self, X):

        X_np = self.scaler.transform(X)
        X_tensor = torch.tensor(X_np, dtype=torch.float32)

        self.rede.eval()

        with torch.no_grad():
            logits = self.rede(X_tensor)
            probas = torch.sigmoid(logits).numpy().flatten()

        return probas

    def predict(self, X):

        probas = self.predict_proba(X)

        return (probas >= 0.5).astype(int)


def treinar_modelo(caminho="data/dataset.csv"):

    df = carregar_dataset(caminho)

    X = df[["horas_uso"]].values
    y = df["alto_risco"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    modelo = ModeloRisco(epocas=200, lr=0.01)

    modelo.fit(X_train, y_train)

    previsoes = modelo.predict(X_test)

    acc = accuracy_score(
        y_test,
        previsoes
    )

    print(f"Acurácia: {acc:.2%}")

    return modelo
