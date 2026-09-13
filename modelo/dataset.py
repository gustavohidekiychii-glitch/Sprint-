import os
import random
import pandas as pd

from .config import CONFIG


def _risco_ponderado(horas, temperatura, distancia_percorrida, carga):
    """
    Combina várias variáveis do equipamento num único score de risco
    (0-100), usado só pra ROTULAR o dataset de treino da IA — ou seja,
    pra ensinar a rede neural qual padrão costuma significar risco alto.
    Não é isso que o sistema usa em produção: depois de treinada, quem
    calcula o risco de verdade é a IA (RiskNet), não essa fórmula.

    Pesos: horas de uso pesa mais (é o principal indicador de desgaste),
    seguido de temperatura, depois distância percorrida e carga.
    """

    risco_horas = min(horas * 10, 100)

    # Temperatura é perigosa nos DOIS sentidos: tanto superaquecimento
    # quanto frio extremo. Definimos uma faixa "normal" (15°C a 35°C)
    # onde o risco de temperatura é 0; fora dela, o risco cresce em
    # qualquer direção, até saturar em 100 a 40°C de distância da faixa.
    FAIXA_MIN, FAIXA_MAX = 15, 35
    fora_da_faixa = max(0, FAIXA_MIN - temperatura, temperatura - FAIXA_MAX)
    risco_temp = min(fora_da_faixa * (100 / 40), 100)

    # distância percorrida e carga já vêm numa escala de 0 a 100
    # (distância em km rodados no período, carga em % da capacidade).
    risco_distancia = max(0, min(distancia_percorrida, 100))
    risco_carga = max(0, min(carga, 100))

    risco_total = (
        risco_horas * 0.40 +
        risco_temp * 0.30 +
        risco_distancia * 0.15 +
        risco_carga * 0.15
    )

    return round(min(risco_total, 100), 1)


def gerar_dataset(n=200):

    dados = []

    for _ in range(n):

        horas = random.randint(1, 12)
        temperatura = round(random.uniform(-20, 80), 1)
        distancia_percorrida = round(random.uniform(0, 100), 1)
        carga = round(random.uniform(0, 100), 1)

        risco = _risco_ponderado(horas, temperatura, distancia_percorrida, carga)

        alto_risco = (
            1 if risco >= CONFIG["limite_alerta"] else 0
        )

        dados.append({
            "horas_uso": horas,
            "temperatura": temperatura,
            "distancia_percorrida": distancia_percorrida,
            "carga_equipamento": carga,
            "risco": risco,
            "alto_risco": alto_risco
        })

    return pd.DataFrame(dados)


def carregar_dataset(caminho="data/dataset.csv"):

    if os.path.exists(caminho):

        df = pd.read_csv(caminho)

        colunas = [
            "horas_uso",
            "temperatura",
            "distancia_percorrida",
            "carga_equipamento",
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
