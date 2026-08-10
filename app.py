from flask import Flask, request, jsonify

from modelo import (
    calcular_risco,
    classificar_uso,
    gerar_recomendacao,
    treinar_modelo
)

app = Flask(__name__)


# Treina a IA quando o servidor inicia
modelo = treinar_modelo()


@app.route("/")
def inicio():

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


if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )