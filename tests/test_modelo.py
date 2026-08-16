from modelo import (
    classificar_uso,
    calcular_risco,
    gerar_recomendacao,
    gerar_dataset,
    ModeloRisco,
    MotorRegras,
    HistoricoRisco,
    atualizar_config,
    avaliar_operacao,
)


def test_classificar_uso():
    assert classificar_uso(2) == "Baixo"
    assert classificar_uso(5) == "Médio"
    assert classificar_uso(10) == "Alto"


def test_calcular_risco():
    assert calcular_risco(1) == 10
    assert calcular_risco(12) == 100  # limitado em 100
    assert calcular_risco(15) == 100


def test_gerar_recomendacao():
    assert "imediata" in gerar_recomendacao(95)
    assert "preventiva" in gerar_recomendacao(75)
    assert "Monitorar" in gerar_recomendacao(55)
    assert "padrões" in gerar_recomendacao(30)


def test_gerar_dataset_colunas():
    df = gerar_dataset(n=20)
    assert list(df.columns) == ["horas_uso", "risco", "alto_risco"]
    assert len(df) == 20


def test_modelo_risco_fit_predict():
    df = gerar_dataset(n=100)
    X = df[["horas_uso"]].values
    y = df["alto_risco"].values

    modelo = ModeloRisco(epocas=50)
    modelo.fit(X, y)

    previsoes = modelo.predict(X)
    assert len(previsoes) == len(y)
    assert set(previsoes.tolist()).issubset({0, 1})


def test_motor_regras_dispara_alerta():
    motor = MotorRegras()
    motor.adicionar_regra("combustivel", "<", 30, "Combustível baixo")

    alertas = motor.avaliar_leitura({"combustivel": 20})
    assert len(alertas) == 1
    assert alertas[0]["mensagem"] == "Combustível baixo"

    # não deve disparar quando dentro do limite
    alertas = motor.avaliar_leitura({"combustivel": 50})
    assert len(alertas) == 0


def test_motor_regras_remover():
    motor = MotorRegras()
    regra = motor.adicionar_regra("temperatura", ">", 90)

    assert motor.remover_regra(regra.id) is True
    assert motor.listar_regras() == []


def test_historico_risco_relatorio():
    historico = HistoricoRisco()

    historico.registrar(horas_uso=2, risco=20, alto_risco=False)
    historico.registrar(horas_uso=9, risco=90, alto_risco=True)

    relatorio = historico.gerar_relatorio()

    assert relatorio["total_registros"] == 2
    assert relatorio["maximo_risco"] == 90
    assert relatorio["minimo_risco"] == 20
    assert relatorio["media_risco"] == 55


def test_avaliar_operacao_modo_bloqueio():
    atualizar_config(limite_alerta=70, modo_operacao="bloqueio")

    resultado = avaliar_operacao(90)
    assert resultado["operacao_bloqueada"] is True

    resultado = avaliar_operacao(30)
    assert resultado["operacao_bloqueada"] is False

    # volta pro modo padrão pra não afetar outros testes
    atualizar_config(modo_operacao="alerta")


def test_atualizar_config_modo_invalido():
    try:
        atualizar_config(modo_operacao="invalido")
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass
