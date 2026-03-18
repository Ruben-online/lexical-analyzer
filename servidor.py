"""
servidor.py — Servidor Flask del prototipo Compilador de Nutrias ;v
Vitally - Fase 1
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from src.lexer import Lexer

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)   # permite llamadas desde cualquier origen (para react)

_lexer = Lexer()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():
    """
    Body esperado (JSON):
        { "codigo": "PACIENTE: Sofia;\nEDAD: 25;" }

    Respuesta:
        {
          "tokens":  [ { tipo, lexema, linea, columna, categoria }, ... ],
          "errores": [ { lexema, linea, columna, mensaje }, ... ],
          "resumen": { total_tokens, total_errores, exitoso }
        }
    """
    data   = request.get_json(silent=True) or {}
    codigo = data.get("codigo", "").strip()

    if not codigo:
        return jsonify({"error": "El campo 'codigo' está vacío"}), 400

    tokens, errores = _lexer.tokenizar(codigo)
    tokens_visibles = [t.to_dict() for t in tokens if t.tipo != "TK_EOF"]

    return jsonify({
        "tokens":  tokens_visibles,
        "errores": [e.to_dict() for e in errores],
        "resumen": {
            "total_tokens":  len(tokens_visibles),
            "total_errores": len(errores),
            "exitoso":       len(errores) == 0
        }
    })

"Modulo de Inicio"
if __name__ == "__main__":
    print("\n  🦦 Compilador de Nutrias — Servidor Léxico")
    print("  ─────────────────────────────────────────")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)