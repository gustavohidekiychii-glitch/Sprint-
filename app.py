from flask import Flask, request, jsonify, render_template

from modelo import (
    CONFIG,
    classificar_uso,
    gerar_recomendacao,
    treinar_modelo,
    atualizar_config,
    avaliar_operacao,
    MotorRegras,
    HistoricoRisco,
)


app = Flask(__name__)


# Treina a IA quando o servidor inicia
modelo = treinar_modelo()

# Motor de regras configuráveis (limites definidos pelo cliente)
motor_regras = MotorRegras()

# Histórico de análises, usado para gerar o relatório de evolução
historico = HistoricoRisco()

# Valores usados quando o cliente não informa uma dessas variáveis.
# Combustível não entra aqui de propósito: a SOMPO indicou que o
# painel do próprio equipamento já mostra isso, então não faz parte
# do cálculo de risco da IA.
PADRAO_TEMPERATURA = 25
PADRAO_VIBRACAO = 0
PADRAO_CARGA = 50


def analisar_com_ia(horas, temperatura=None, vibracao=None, carga=None):
    """
    Roda a IA (rede neural) com as 4 variáveis do equipamento e monta
    o resultado padrão usado tanto em /api/risco quanto em /api/monitorar.
    O risco não é mais uma fórmula fixa (ex: "1 hora = 10%") — é a
    própria rede neural quem calcula, com base nas variáveis recebidas.
    """

    temperatura = PADRAO_TEMPERATURA if temperatura is None else temperatura
    vibracao = PADRAO_VIBRACAO if vibracao is None else vibracao
    carga = PADRAO_CARGA if carga is None else carga

    entrada = [[horas, temperatura, vibracao, carga]]

    risco = round(float(modelo.predict_risco(entrada)[0]), 1)

    # "Alto risco" usa o MESMO limite configurável do resto do sistema
    # (o mesmo que decide o bloqueio) — assim não existem dois critérios
    # diferentes pra risco alto dependendo de qual parte do código olha.
    alto_risco = risco >= CONFIG["limite_alerta"]

    operacao = avaliar_operacao(risco)

    historico.registrar(
        horas_uso=horas,
        risco=risco,
        alto_risco=alto_risco
    )

    return {
        "horas_uso": horas,
        "temperatura": temperatura,
        "vibracao": vibracao,
        "carga_equipamento": carga,
        "risco": risco,
        "nivel_uso": classificar_uso(horas),
        "alto_risco": alto_risco,
        "recomendacao": gerar_recomendacao(risco),
        "operacao_bloqueada": operacao["operacao_bloqueada"],
        "modo_operacao": operacao["modo_operacao"]
    }


@app.route("/")
def boas_vindas():

    return render_template("welcome.html")


@app.route("/painel")
def inicio():

    return render_template("index.html")


@app.route("/api/status")
def status():

    return jsonify({
        "sistema": "Vortex",
        "status": "online"
    })


@app.route("/api/risco", methods=["POST"])
def analisar_risco():
    """
    Analisa o risco do equipamento com a IA. 'horas_uso' é
    obrigatório; 'temperatura', 'vibracao' e 'carga_equipamento' são
    opcionais (assumem um valor padrão quando não informados).
    """

    dados = request.get_json()

    if not dados or "horas_uso" not in dados:

        return jsonify({
            "erro": "Informe 'horas_uso'."
        }), 400

    resultado = analisar_com_ia(
        horas=dados["horas_uso"],
        temperatura=dados.get("temperatura"),
        vibracao=dados.get("vibracao"),
        carga=dados.get("carga_equipamento")
    )

    return jsonify(resultado)


# ---------------------------------------------------------
# Configuração operacional (limite de risco + modo alerta/bloqueio)
# ---------------------------------------------------------

@app.route("/api/configuracao", methods=["GET"])
def obter_configuracao():

    return jsonify(CONFIG)


@app.route("/api/configuracao", methods=["POST"])
def definir_configuracao():
    """
    Body esperado (todos os campos são opcionais):
    {
        "limite_alerta": 70,
        "modo_operacao": "alerta"   // ou "bloqueio"
    }
    """

    dados = request.get_json() or {}

    try:
        config_atualizada = atualizar_config(
            limite_alerta=dados.get("limite_alerta"),
            modo_operacao=dados.get("modo_operacao")
        )

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    return jsonify(config_atualizada)


# ---------------------------------------------------------
# Regras configuráveis (limites definidos pelo cliente)
# ---------------------------------------------------------

@app.route("/api/regras", methods=["GET"])
def listar_regras():

    return jsonify({
        "regras": motor_regras.listar_regras()
    })


@app.route("/api/regras", methods=["POST"])
def criar_regra():
    """
    Body esperado:
    {
        "variavel": "combustivel",
        "operador": "<",
        "limite": 30,
        "mensagem": "Combustível abaixo do limite definido"  (opcional)
    }
    """

    dados = request.get_json()

    campos_obrigatorios = ["variavel", "operador", "limite"]

    if not dados or not all(c in dados for c in campos_obrigatorios):
        return jsonify({
            "erro": f"Informe os campos: {campos_obrigatorios}"
        }), 400

    try:
        regra = motor_regras.adicionar_regra(
            variavel=dados["variavel"],
            operador=dados["operador"],
            limite=dados["limite"],
            mensagem=dados.get("mensagem")
        )

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    return jsonify(regra.to_dict()), 201


@app.route("/api/regras/<int:id_regra>", methods=["DELETE"])
def remover_regra(id_regra):

    removida = motor_regras.remover_regra(id_regra)

    if not removida:
        return jsonify({"erro": "Regra não encontrada."}), 404

    return jsonify({"removida": True, "id": id_regra})


# ---------------------------------------------------------
# Monitoramento: aplica as regras + (opcional) a IA
# ---------------------------------------------------------

@app.route("/api/monitorar", methods=["POST"])
def monitorar():
    """
    Recebe uma leitura do equipamento com quantas variáveis o cliente
    quiser (as regras configuráveis aceitam qualquer nome), ex:

    {
        "temperatura": 95,
        "horas_uso": 9
    }

    Retorna os alertas de regras violadas e, se 'horas_uso' estiver
    presente, também o score da IA (calculado com 'temperatura',
    'vibracao' e 'carga_equipamento', quando informados).
    """

    leitura = request.get_json()

    if not leitura:
        return jsonify({
            "erro": "Envie um objeto JSON com as leituras do equipamento."
        }), 400

    alertas = motor_regras.avaliar_leitura(leitura)

    resposta = {
        "leitura": leitura,
        "alertas": alertas,
        "total_alertas": len(alertas)
    }

    # Se vier horas_uso, aproveita e já roda a IA também
    if "horas_uso" in leitura:

        resposta["analise_ia"] = analisar_com_ia(
            horas=leitura["horas_uso"],
            temperatura=leitura.get("temperatura"),
            vibracao=leitura.get("vibracao"),
            carga=leitura.get("carga_equipamento")
        )

    return jsonify(resposta)


# ---------------------------------------------------------
# Relatório de evolução do risco
# ---------------------------------------------------------

@app.route("/api/relatorio", methods=["GET"])
def relatorio():
    """
    Retorna estatísticas (média, máximo, mínimo), a tendência
    do risco (aumento/reducao/estavel) e o histórico completo
    de análises já realizadas.
    """

    return jsonify(historico.gerar_relatorio())


if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
