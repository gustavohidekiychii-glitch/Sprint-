import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
from sklearn.neural_network import MLPRegressor

from .dataset import carregar_dataset


class RiskNet:
    """
    Rede neural simples para prever o risco do equipamento
    de 0 a 100.

    A implementação usa o MLPRegressor do scikit-learn,
    evitando a dependência pesada do PyTorch.
    """

    def __init__(self, entrada=4, oculta=16):
        self.rede = MLPRegressor(
            hidden_layer_sizes=(oculta, oculta),
            activation="relu",
            solver="adam",
            learning_rate_init=0.01,
            max_iter=300,
            random_state=42
        )

    def fit(self, X, y):
        self.rede.fit(X, y)
        return self

    def predict(self, X):
        return self.rede.predict(X)


class ModeloRisco:
    """
    Modelo de rede neural responsável por prever
    um valor contínuo de risco entre 0 e 100.
    """

    def __init__(self, epocas=300, lr=0.01):
        self.epocas = epocas
        self.lr = lr

        self.scaler = StandardScaler()

        self.rede = RiskNet()

    def fit(self, X, y_risco):
        """
        Treina a rede neural utilizando os dados
        de risco do dataset.
        """

        X_np = self.scaler.fit_transform(X)

        y_np = np.array(y_risco, dtype="float32")

        self.rede.fit(X_np, y_np)

        return self

    def predict_risco(self, X):
        """
        Retorna o risco previsto entre 0 e 100.
        """

        X_np = self.scaler.transform(X)

        previsoes = self.rede.predict(X_np)

        # Garante que o risco nunca fique abaixo de 0
        # ou acima de 100.
        previsoes = np.clip(previsoes, 0, 100)

        return previsoes

    def predict(self, X):
        """
        Retorna 1 para risco alto e 0 para risco baixo.
        """

        riscos = self.predict_risco(X)

        return (riscos >= 50).astype(int)


def treinar_modelo(caminho="data/dataset.csv"):

    df = carregar_dataset(caminho)

    X = df[
        [
            "horas_uso",
            "temperatura",
            "distancia_percorrida",
            "carga_equipamento"
        ]
    ].values

    y = df["risco"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    modelo = ModeloRisco(
        epocas=300,
        lr=0.01
    )

    modelo.fit(X_train, y_train)

    previsoes = modelo.predict_risco(X_test)

    erro_medio = mean_absolute_error(
        y_test,
        previsoes
    )

    print(
        f"Erro médio do risco previsto: "
        f"{erro_medio:.1f} pontos (de 0 a 100)"
    )

    return modelo