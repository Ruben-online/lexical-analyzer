"""
servidor.py — Servidor Flask del Compilador de Nutrias
Vitally — Fase 1 (Léxico) + Fase 2 (Sintáctico)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from lexer   import Lexer
from parser  import Parser, arbol_a_texto, arbol_a_dict

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
_lexer = Lexer()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():
    """Fase 1 — Léxico."""
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


@app.route("/parsear", methods=["POST"])
def parsear():
    """Fase 1 + 2 — Léxico + Sintáctico."""
    data   = request.get_json(silent=True) or {}
    codigo = data.get("codigo", "").strip()
    if not codigo:
        return jsonify({"error": "El campo 'codigo' está vacío"}), 400

    # Fase 1
    tokens, errores_lexicos = _lexer.tokenizar(codigo)
    tokens_visibles = [t.to_dict() for t in tokens if t.tipo != "TK_EOF"]

    if errores_lexicos:
        return jsonify({
            "tokens": tokens_visibles,
            "errores_lexicos": [e.to_dict() for e in errores_lexicos],
            "arbol_texto": None, "arbol_dict": None,
            "error_sintactico": None,
            "resumen": {"exitoso": False, "fase_exitosa": "ninguna",
                        "mensaje": "Compilacion detenida: errores lexicos"}
        })

    # Fase 2
    parser = Parser(tokens)
    arbol, error_sint = parser.parsear()

    if error_sint:
        return jsonify({
            "tokens": tokens_visibles, "errores_lexicos": [],
            "arbol_texto": None, "arbol_dict": None,
            "error_sintactico": error_sint.to_dict(),
            "resumen": {"exitoso": False, "fase_exitosa": "lexica",
                        "mensaje": str(error_sint)}
        })

    # Exito
    texto = arbol_a_texto(arbol, "", True)
    return jsonify({
        "tokens": tokens_visibles, "errores_lexicos": [],
        "arbol_texto": texto,
        "arbol_dict":  arbol_a_dict(arbol),
        "error_sintactico": None,
        "resumen": {"exitoso": True, "fase_exitosa": "completa",
                    "mensaje": "Cadena aceptada"}
    })


if __name__ == "__main__":
    print("\n  Compilador de Nutrias — Fase 1 + 2")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)
