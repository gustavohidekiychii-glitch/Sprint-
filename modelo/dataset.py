import os
import random
import pandas as pd

from .config import CONFIG
from .regras import calcular_risco


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


def carregar_dataset(caminho="data/dataset.csv"):

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
