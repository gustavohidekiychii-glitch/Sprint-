from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from modelo.config import CONFIG
from modelo.dataset import carregar_dataset
from modelo.rede_neural import ModeloRisco


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "dataset.csv"

FEATURES = [
    "horas_uso",
    "temperatura",
    "distancia_percorrida",
    "carga_equipamento",
]

NOMES = {
    "horas_uso": "Horas de uso",
    "temperatura": "Temperatura (°C)",
    "distancia_percorrida": "Distância percorrida",
    "carga_equipamento": "Carga do equipamento (%)",
}


st.set_page_config(
    page_title="Vortex | Análise de Risco",
    page_icon="🚜",
    layout="wide",
)


@st.cache_resource(show_spinner="Treinando a rede neural...")
def carregar_modelo():
    """Treina o mesmo MLP usado pelo backend e calcula o MAE de teste."""
    df = carregar_dataset(str(DATASET_PATH))

    faltantes = [coluna for coluna in FEATURES + ["risco"] if coluna not in df.columns]
    if faltantes:
        raise ValueError(
            "A base de dados não contém as colunas necessárias: "
            + ", ".join(faltantes)
        )

    X = df[FEATURES].astype(float).values
    y = df["risco"].astype(float).values

    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    modelo = ModeloRisco(epocas=300, lr=0.01)
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict_risco(X_teste)
    mae = float(mean_absolute_error(y_teste, previsoes))

    # Referências usadas na explicação: medianas calculadas somente
    # na parte de treinamento da base.
    referencias = pd.DataFrame(X_treino, columns=FEATURES).median()

    return modelo, df, mae, referencias


def explicar_drivers(modelo, entrada, referencias, score_atual):
    """
    Estima a sensibilidade local substituindo uma variável por vez
    pela mediana observada no conjunto de treinamento.
    Não representa causalidade nem uma explicação causal do modelo.
    """
    resultados = []

    for indice, coluna in enumerate(FEATURES):
        contrafactual = entrada.copy()
        contrafactual[0, indice] = float(referencias[coluna])

        score_referencia = float(modelo.predict_risco(contrafactual)[0])
        impacto = score_atual - score_referencia

        if impacto >= 1:
            leitura = "Eleva o score em relação à referência"
        elif impacto <= -1:
            leitura = "Reduz o score em relação à referência"
        else:
            leitura = "Impacto pequeno perto da referência"

        resultados.append(
            {
                "Variável": NOMES[coluna],
                "Valor informado": round(float(entrada[0, indice]), 2),
                "Referência da base": round(float(referencias[coluna]), 2),
                "Variação estimada (pontos)": round(impacto, 2),
                "Interpretação": leitura,
            }
        )

    return pd.DataFrame(resultados).assign(
        magnitude=lambda tabela: tabela["Variação estimada (pontos)"].abs()
    ).sort_values("magnitude", ascending=False).drop(columns="magnitude")


st.title("🚜 Vortex — Monitoramento inteligente de risco")
st.write(
    "Informe as condições do equipamento para estimar o score de risco "
    "e visualizar quais variáveis mais influenciam o resultado neste cenário."
)

try:
    modelo, df, mae, referencias = carregar_modelo()
except Exception as erro:
    st.error(f"Não foi possível carregar ou treinar o modelo: {erro}")
    st.stop()


with st.sidebar:
    st.header("Configurações")
    limite_alerta = st.slider(
        "Limite para risco alto",
        min_value=50,
        max_value=90,
        value=int(CONFIG.get("limite_alerta", 70)),
        step=5,
        help="O limite altera a classificação exibida, mas não modifica o treinamento da rede neural.",
    )
    st.divider()
    st.caption("Modelo de Machine Learning")
    st.write("Rede neural MLPRegressor")
    st.write("Duas camadas ocultas com 16 neurônios cada")
    st.write("Divisão de avaliação: 80% treino / 20% teste")
    st.metric("Erro médio absoluto (MAE)", f"{mae:.2f} pontos")
    st.caption("O MAE é calculado no conjunto de teste da base atual.")


st.subheader("1. Dados do equipamento")
with st.form("formulario_equipamento"):
    col1, col2 = st.columns(2)

    with col1:
        horas = st.slider(
            "Horas de uso",
            min_value=1.0,
            max_value=12.0,
            value=8.0,
            step=0.5,
            help="Faixa disponível na base de treinamento: 1 a 12 horas.",
        )
        temperatura = st.slider(
            "Temperatura (°C)",
            min_value=-20.0,
            max_value=80.0,
            value=25.0,
            step=0.5,
            help="Faixa disponível na base de treinamento: -20 °C a 80 °C.",
        )

    with col2:
        distancia = st.slider(
            "Distância percorrida",
            min_value=0.0,
            max_value=100.0,
            value=40.0,
            step=1.0,
            help="Valor na escala de 0 a 100 utilizada pelo dataset.",
        )
        carga = st.slider(
            "Carga do equipamento (%)",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0,
            help="Valor percentual na escala de 0 a 100.",
        )

    enviar = st.form_submit_button(
        "Analisar risco do equipamento",
        type="primary",
        use_container_width=True,
    )


if enviar:
    entrada = np.array([[horas, temperatura, distancia, carga]], dtype=float)
    score = float(modelo.predict_risco(entrada)[0])
    score = float(np.clip(score, 0, 100))

    if score >= limite_alerta:
        nivel = "ALTO"
        st.error("Risco alto — recomenda-se avaliar o equipamento antes de continuar a operação.")
        if score >= 90:
            recomendacao = "Priorizar avaliação e manutenção imediata."
        else:
            recomendacao = "Agendar manutenção preventiva e acompanhar o equipamento."
    elif score >= 50:
        nivel = "MÉDIO"
        st.warning("Risco médio — recomenda-se acompanhar as condições do equipamento.")
        recomendacao = "Monitorar o equipamento com maior frequência."
    else:
        nivel = "BAIXO"
        st.success("Risco baixo — o cenário está dentro da faixa de atenção definida.")
        recomendacao = "Manter o monitoramento e as práticas regulares de manutenção."

    st.divider()
    st.subheader("2. Resultado da análise")

    a, b, c = st.columns(3)
    a.metric("Score de risco", f"{score:.1f} / 100")
    b.metric("Classificação", nivel)
    c.metric("Limite configurado", f"{limite_alerta} pontos")

    st.progress(int(round(score)))
    st.info(f"**Recomendação:** {recomendacao}")

    st.subheader("3. Principais fatores (drivers)")
    st.write(
        "A tabela compara o cenário informado com uma referência mediana da base "
        "de treinamento, substituindo uma variável por vez e recalculando a previsão."
    )

    drivers = explicar_drivers(modelo, entrada, referencias, score)
    st.dataframe(
        drivers,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Variação estimada (pontos)": st.column_config.NumberColumn(
                "Variação estimada (pontos)",
                format="%+.2f",
            )
        },
    )

    grafico = drivers.set_index("Variável")[["Variação estimada (pontos)"]]
    st.bar_chart(grafico)

    st.caption(
        "Interpretação: valores positivos indicam que a variável informada eleva "
        "o score em comparação com sua referência; valores negativos indicam redução. "
        "É uma análise de sensibilidade local, não uma relação causal."
    )

else:
    st.info("Preencha os dados e clique em **Analisar risco do equipamento** para visualizar o resultado.")


with st.expander("Sobre a base de dados e as limitações do modelo"):
    st.write(
        f"A base carregada contém **{len(df)} registros** e as variáveis "
        "utilizadas no treinamento, além do score de risco."
    )
    st.write(
        "A base atual é sintética/de demonstração. O score usado como alvo foi "
        "calculado por regras ponderadas e a rede neural aprende a reproduzir "
        "esse padrão. Portanto, o MAE mede a aproximação desse score de referência, "
        "não a capacidade comprovada de prever sinistros reais."
    )
    st.write(
        "Antes de uso operacional ou decisões de seguro, o modelo precisa ser "
        "validado com dados reais, históricos de manutenção e sinistros, além de "
        "avaliações com especialistas."
    )
    st.write("Colunas de entrada: horas de uso, temperatura, distância percorrida e carga do equipamento.")


st.divider()
st.caption(
    "Vortex — Inteligência Preventiva para Equipamentos Agrícolas com IA | "
    "Aplicação demonstrativa. Não substitui inspeção técnica ou avaliação especializada."
)
