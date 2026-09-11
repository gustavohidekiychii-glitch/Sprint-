import numpy as np
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error

from .dataset import carregar_dataset


class RiskNet(nn.Module):
    """
    Rede neural simples (Multilayer Perceptron) que prevê o risco do
    equipamento (0 a 100) a partir de 4 variáveis: horas_uso,
    temperatura, vibracao e carga_equipamento.
    """

    def __init__(self, entrada=4, oculta=16):
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
    Wrapper em torno da RiskNet. Diferente de um classificador
    (que só diz "é alto risco: sim/não"), esse modelo faz REGRESSÃO —
    prevê diretamente um valor contínuo de risco entre 0 e 100, o que
    dá uma resposta graduada em vez de um "tudo ou nada".
    """

    def __init__(self, epocas=300, lr=0.01):
        self.epocas = epocas
        self.lr = lr
        self.scaler = StandardScaler()
        self.rede = RiskNet()

    def fit(self, X, y_risco):
        """
        y_risco: valores contínuos de 0 a 100 (não é mais 0/1).
        """

        X_np = self.scaler.fit_transform(X)

        # normaliza o alvo de 0-100 para 0-1, pra combinar com a
        # sigmoid da saída da rede
        y_np = (np.array(y_risco, dtype="float32") / 100.0).reshape(-1, 1)

        X_tensor = torch.tensor(X_np, dtype=torch.float32)
        y_tensor = torch.tensor(y_np, dtype=torch.float32)

        criterio = nn.MSELoss()
        otimizador = torch.optim.Adam(
            self.rede.parameters(), lr=self.lr
        )

        self.rede.train()

        for _ in range(self.epocas):

            otimizador.zero_grad()

            saida = torch.sigmoid(self.rede(X_tensor))
            perda = criterio(saida, y_tensor)

            perda.backward()
            otimizador.step()

        return self

    def predict_risco(self, X):
        """Retorna o risco previsto (0 a 100) para cada linha de X."""

        X_np = self.scaler.transform(X)
        X_tensor = torch.tensor(X_np, dtype=torch.float32)

        self.rede.eval()

        with torch.no_grad():
            saida = torch.sigmoid(self.rede(X_tensor))

        return saida.numpy().flatten() * 100

    def predict(self, X):
        """Atalho: 1 se o risco previsto for >= 50, senão 0."""

        riscos = self.predict_risco(X)

        return (riscos >= 50).astype(int)


def treinar_modelo(caminho="data/dataset.csv"):

    df = carregar_dataset(caminho)

    X = df[["horas_uso", "temperatura", "vibracao", "carga_equipamento"]].values
    y = df["risco"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    modelo = ModeloRisco(epocas=300, lr=0.01)

    modelo.fit(X_train, y_train)

    previsoes = modelo.predict_risco(X_test)

    erro_medio = mean_absolute_error(y_test, previsoes)

    print(f"Erro médio do risco previsto: {erro_medio:.1f} pontos (de 0 a 100)")

    return modelo
