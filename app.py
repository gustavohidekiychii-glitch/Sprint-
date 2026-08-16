from flask import Flask, request, jsonify, render_template

from modelo import (
    CONFIG,
    calcular_risco,
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


@app.route("/")
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

    dados = request.get_json()

    if not dados or "horas_uso" not in dados:

        return jsonify({
            "erro": "Informe 'horas_uso'."
        }), 400

    horas = dados["horas_uso"]

    risco = calcular_risco(horas)

    nivel = classificar_uso(horas)

    recomendacao = gerar_recomendacao(risco)

    previsao = modelo.predict([[horas]])[0]

    operacao = avaliar_operacao(risco)

    historico.registrar(
        horas_uso=horas,
        risco=risco,
        alto_risco=bool(previsao)
    )

    return jsonify({
        "horas_uso": horas,
        "risco": risco,
        "nivel_uso": nivel,
        "alto_risco": bool(previsao),
        "recomendacao": recomendacao,
        "operacao_bloqueada": operacao["operacao_bloqueada"],
        "modo_operacao": operacao["modo_operacao"]
    })


@app.route("/api/configuracao", methods=["GET"])
def obter_configuracao():

    return jsonify(CONFIG)


@app.route("/api/configuracao", methods=["POST"])
def definir_configuracao():


    dados = request.get_json() or {}

    try:
        config_atualizada = atualizar_config(
            limite_alerta=dados.get("limite_alerta"),
            modo_operacao=dados.get("modo_operacao")
        )

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    return jsonify(config_atualizada)


@app.route("/api/regras", methods=["GET"])
def listar_regras():

    return jsonify({
        "regras": motor_regras.listar_regras()
    })


@app.route("/api/regras", methods=["POST"])
def criar_regra():

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



@app.route("/api/monitorar", methods=["POST"])
def monitorar():

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

        horas = leitura["horas_uso"]

        risco = calcular_risco(horas)
        previsao = modelo.predict([[horas]])[0]

        operacao = avaliar_operacao(risco)

        historico.registrar(
            horas_uso=horas,
            risco=risco,
            alto_risco=bool(previsao)
        )

        resposta["analise_ia"] = {
            "risco": risco,
            "nivel_uso": classificar_uso(horas),
            "alto_risco": bool(previsao),
            "recomendacao": gerar_recomendacao(risco),
            "operacao_bloqueada": operacao["operacao_bloqueada"],
            "modo_operacao": operacao["modo_operacao"]
        }

    return jsonify(resposta)


@app.route("/api/relatorio", methods=["GET"])
def relatorio():
    return jsonify(historico.gerar_relatorio())


if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
