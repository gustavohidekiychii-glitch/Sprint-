import os
import random
import pandas as pd

from .config import CONFIG


def _risco_ponderado(horas, temperatura, vibracao, carga):
    """
    Combina várias variáveis do equipamento num único score de risco
    (0-100), usado só pra ROTULAR o dataset de treino da IA — ou seja,
    pra ensinar a rede neural qual padrão costuma significar risco alto.
    Não é isso que o sistema usa em produção: depois de treinada, quem
    calcula o risco de verdade é a IA (RiskNet), não essa fórmula.

    Pesos: horas de uso pesa mais (é o principal indicador de desgaste),
    seguido de temperatura, depois vibração e carga.
    """

    risco_horas = min(horas * 10, 100)

    # Abaixo de 30°C consideramos operação normal; acima disso, o risco
    # cresce até 70°C (que já representa risco máximo).
    risco_temp = max(0, min((temperatura - 30) * (100 / 40), 100))

    # vibração e carga já vêm numa escala de 0 a 100.
    risco_vibracao = max(0, min(vibracao, 100))
    risco_carga = max(0, min(carga, 100))

    risco_total = (
        risco_horas * 0.40 +
        risco_temp * 0.30 +
        risco_vibracao * 0.15 +
        risco_carga * 0.15
    )

    return round(min(risco_total, 100), 1)


def gerar_dataset(n=200):

    dados = []

    for _ in range(n):

        horas = random.randint(1, 12)
        temperatura = round(random.uniform(20, 70), 1)
        vibracao = round(random.uniform(0, 100), 1)
        carga = round(random.uniform(0, 100), 1)

        risco = _risco_ponderado(horas, temperatura, vibracao, carga)

        alto_risco = (
            1 if risco >= CONFIG["limite_alerta"] else 0
        )

        dados.append({
            "horas_uso": horas,
            "temperatura": temperatura,
            "vibracao": vibracao,
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
            "vibracao",
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
