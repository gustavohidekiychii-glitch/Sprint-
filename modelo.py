import os
import random
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


CONFIG = {
    "limite_alerta": 70,
    "modo_operacao": "alerta"
}


def classificar_uso(horas):

    if horas < 4:
        return "Baixo"

    elif horas < 8:
        return "Médio"

    else:
        return "Alto"


def calcular_risco(horas):

    return min(horas * 10, 100)


def gerar_recomendacao(risco):

    if risco >= 90:
        return "Realizar manutenção imediata."

    elif risco >= 70:
        return "Agendar manutenção preventiva."

    elif risco >= 50:
        return "Monitorar equipamento com maior frequência."

    else:
        return "Operação dentro dos padrões."


def gerar_dataset(n=200):

    dados = []

    for _ in range(n):

        horas = random.randint(1, 12)
        risco = calcular_risco(horas)

        alto_risco = (
            1 if risco >= CONFIG["limite_alerta"] else 0
        )

        dados.append({
            "horas_uso": horas,
            "risco": risco,
            "alto_risco": alto_risco
        })

    return pd.DataFrame(dados)


def carregar_dataset(caminho="dataset.csv"):

    if os.path.exists(caminho):

        df = pd.read_csv(caminho)

        colunas = [
            "horas_uso",
            "risco",
            "alto_risco"
        ]

        for coluna in colunas:

            if coluna not in df.columns:
                raise ValueError(
                    f"A coluna '{coluna}' não existe."
                )

        return df

    return gerar_dataset()

def treinar_modelo(caminho="dataset.csv"):

    df = carregar_dataset(caminho)

    X = df[["horas_uso"]]
    y = df["alto_risco"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    modelo = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )

    modelo.fit(X_train, y_train)

    previsoes = modelo.predict(X_test)

    acc = accuracy_score(
        y_test,
        previsoes
    )

    print(f"Acurácia: {acc:.2%}")

    return modelo