import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from lexer     import Lexer
from parser    import Parser, arbol_a_texto, arbol_a_dict
from semantico import AnalizadorSemantico, ErrorSemantico
from gemini    import generar_plan

app    = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
_lexer = Lexer()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/compilar", methods=["POST"])
def compilar():
    data       = request.get_json(silent=True) or {}
    codigo     = data.get("codigo", "").strip()
    pedir_plan = data.get("generar", False)

    if not codigo:
        return jsonify({"error": "Código vacío"}), 400

    resultado = {
        "tokens": [], "errores_lexicos": [],
        "arbol_texto": None, "arbol_dict": None,
        "error_sintactico": None, "tabla_simbolos": None,
        "error_semantico": None, "plan_clinico": None,
        "prompt_generado": None, "modelo_usado": None,
        "advertencia": None,
        "resumen": {"exitoso": False, "fase_exitosa": "ninguna", "mensaje": ""}
    }

    # Fase 1 — Léxico
    tokens, errores_lex = _lexer.tokenizar(codigo)
    resultado["tokens"] = [t.to_dict() for t in tokens if t.tipo != "TK_EOF"]
    if errores_lex:
        resultado["errores_lexicos"] = [e.to_dict() for e in errores_lex]
        resultado["resumen"] = {"exitoso": False, "fase_exitosa": "ninguna",
                                "mensaje": f"{len(errores_lex)} error(es) léxico(s)"}
        return jsonify(resultado)

    # Fase 2 — Sintáctico
    parser = Parser(tokens)
    arbol, error_sint = parser.parsear()
    if error_sint:
        resultado["error_sintactico"] = error_sint.to_dict()
        resultado["resumen"] = {"exitoso": False, "fase_exitosa": "lexica",
                                "mensaje": str(error_sint)}
        return jsonify(resultado)
    resultado["arbol_texto"] = arbol_a_texto(arbol, "", True)
    resultado["arbol_dict"]  = arbol_a_dict(arbol)

    # Fase 3 — Semántico
    sem = AnalizadorSemantico()
    try:
        tabla = sem.analizar(arbol)
        resultado["tabla_simbolos"] = tabla.to_dict()
    except ErrorSemantico as e:
        resultado["error_semantico"] = e.to_dict()
        resultado["resumen"] = {"exitoso": False, "fase_exitosa": "sintactica",
                                "mensaje": e.mensaje}
        return jsonify(resultado)

    # Fase 4 — Gemini
    if pedir_plan:
        gen = generar_plan(tabla)
        resultado["plan_clinico"]    = gen["plan"]
        resultado["prompt_generado"] = gen.get("prompt", "")
        resultado["modelo_usado"]    = gen.get("modelo_usado", "DEMO")
        resultado["advertencia"]     = gen.get("advertencia")
        es_demo = resultado["modelo_usado"] == "DEMO"
        resultado["resumen"] = {
            "exitoso": True, "fase_exitosa": "completa",
            "mensaje": "DEMO activo" if es_demo else f"Plan generado con {resultado['modelo_usado']}"
        }
    else:
        resultado["resumen"] = {"exitoso": True, "fase_exitosa": "semantica",
                                "mensaje": "Análisis completo — presiona Generar Plan"}

    return jsonify(resultado)


if __name__ == "__main__":
    print("\n  🦦 Compilador de Nutrias — Modo Caso de Uso")
    print("  Formulario + Editor + Compilador + Gemini")
    print("  ─────────────────────────────────────────")
    print("  http://localhost:5000\n")
    app.run()
