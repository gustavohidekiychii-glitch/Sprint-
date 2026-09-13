from modelo import (
    classificar_uso,
    gerar_recomendacao,
    gerar_dataset,
    ModeloRisco,
    MotorRegras,
    HistoricoRisco,
    atualizar_config,
    avaliar_operacao,
    validar_leitura,
)


def test_classificar_uso():
    assert classificar_uso(2) == "Baixo"
    assert classificar_uso(5) == "Médio"
    assert classificar_uso(10) == "Alto"


def test_gerar_recomendacao():
    assert "imediata" in gerar_recomendacao(95)
    assert "preventiva" in gerar_recomendacao(75)
    assert "Monitorar" in gerar_recomendacao(55)
    assert "padrões" in gerar_recomendacao(30)


def test_gerar_dataset_colunas():
    df = gerar_dataset(n=20)
    assert list(df.columns) == [
        "horas_uso", "temperatura", "distancia_percorrida",
        "carga_equipamento", "risco", "alto_risco"
    ]
    assert len(df) == 20
    # combustível não faz parte do cálculo de risco (indicação da SOMPO:
    # o painel do próprio equipamento já mostra isso)
    assert "combustivel" not in df.columns


def test_modelo_risco_fit_predict():
    df = gerar_dataset(n=100)
    X = df[["horas_uso", "temperatura", "distancia_percorrida", "carga_equipamento"]].values
    y = df["risco"].values  # alvo contínuo (0-100), não mais 0/1

    modelo = ModeloRisco(epocas=100)
    modelo.fit(X, y)

    riscos = modelo.predict_risco(X)
    assert len(riscos) == len(y)
    assert all(0 <= r <= 100 for r in riscos)

    previsoes = modelo.predict(X)
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


def test_validar_leitura_rejeita_valor_impossivel():
    # -1000°C é fisicamente impossível — deve ser rejeitado, não calculado
    try:
        validar_leitura(temperatura=-1000)
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass


def test_validar_leitura_aceita_valores_normais():
    # não deve levantar erro nenhum
    validar_leitura(horas_uso=8, temperatura=30, distancia_percorrida=40, carga_equipamento=60)


def test_validar_variavel_ignora_nome_desconhecido():
    # variáveis de regras customizadas (sem limite físico conhecido)
    # não devem ser bloqueadas por este módulo
    from modelo.validacao import validar_variavel
    validar_variavel("pressao_pneu", 9999)  # não deve levantar erro
