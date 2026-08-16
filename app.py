from flask import Flask, request, jsonify, render_template

from modelo import (
    calcular_risco,
    classificar_uso,
    gerar_recomendacao,
    treinar_modelo,
    MotorRegras,
)


app = Flask(__name__)


# Treina a IA quando o servidor inicia
modelo = treinar_modelo()

# Motor de regras configuráveis (limites definidos pelo cliente)
motor_regras = MotorRegras()

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

    return jsonify({
        "horas_uso": horas,
        "risco": risco,
        "nivel_uso": nivel,
        "alto_risco": bool(previsao),
        "recomendacao": recomendacao
    })

# Regras configuráveis User Story 3

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


@app.route("/api/monitorar", methods=["POST"])
def monitorar():
    """
    Recebe uma leitura do equipamento com quantas variáveis
    o cliente quiser, ex:

    {
        "combustivel": 25,
        "temperatura": 95,
        "horas_uso": 9
    }

    Retorna os alertas de regras violadas e, se 'horas_uso'
    estiver presente, também o score da IA.
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

        horas = leitura["horas_uso"]

        risco = calcular_risco(horas)
        previsao = modelo.predict([[horas]])[0]

        resposta["analise_ia"] = {
            "risco": risco,
            "nivel_uso": classificar_uso(horas),
            "alto_risco": bool(previsao),
            "recomendacao": gerar_recomendacao(risco)
        }

    return jsonify(resposta)


if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
