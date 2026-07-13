from flask import Flask, render_template, request, redirect, url_for, flash, g
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "chave_secreta_aqui" # troca por uma chave sua
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def converter_valor(valor_str):
    """Converte 2.700,50 ou 2700,50 ou 2700.50 para float"""
    if not valor_str:
        raise ValueError("Valor vazio")
    valor_str = valor_str.replace('.', '').replace(',', '.') # tira ponto de milhar e troca virgula por ponto
    return float(valor_str)

@app.route("/", methods=["GET"])
def index():
    # Coloca aqui sua lógica pra carregar dados da tela
    return render_template("index.html") 

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario_str = request.form.get("salario", "").strip()
        if not salario_str:
            flash("Digite um valor para o salário", "error")
            return redirect(url_for("index"))
            
        salario = converter_valor(salario_str) 

        db = get_db()
        db.execute("UPDATE settings SET valor = ? WHERE chave='salario_mes'", (salario,))
        db.execute("DELETE FROM transactions") 
        db.commit()
        flash(f"Salário de R$ {salario:.2f} dividido com sucesso!", "success")

    except ValueError:
        flash("Valor inválido. Use 2700 ou 2.700,50", "error")
    except Exception as e:
        flash(f"Erro ao salvar salário: {str(e)}", "error")
        
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    try:
        categoria_id = request.form.get("categoria_id")
        valor_str = request.form.get("valor", "").strip()
        descricao = request.form.get("descricao", "")

        if not categoria_id or not valor_str:
            flash("Preencha categoria e valor", "error")
            return redirect(url_for("index"))

        valor = converter_valor(valor_str)
        categoria_id = int(categoria_id)
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        db.execute(
            "INSERT INTO transactions (categoria_id, valor, descricao, data) VALUES (?,?,?,?)", 
            (categoria_id, valor, descricao, data)
        )
        db.commit()
        flash("Gasto lançado!", "success")

    except ValueError:
        flash("Valor inválido. Use 2700 ou 2.700,50", "error")
    except Exception as e:
        flash(f"Erro ao salvar gasto: {str(e)}", "error")

    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)