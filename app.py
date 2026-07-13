from flask import Flask, render_template, request, redirect, url_for, flash, g
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "troca_essa_chave_por_uma_aleatoria"
DATABASE = 'ajuda_custo.db'

# Cria o banco se não existir
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS settings (
                        chave TEXT PRIMARY KEY,
                        valor REAL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        categoria_id INTEGER,
                        valor REAL,
                        descricao TEXT,
                        data TEXT,
                        FOREIGN KEY (categoria_id) REFERENCES categories(id))''')
        # Insere categorias padrão
        cats = db.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if cats == 0:
            db.executemany("INSERT INTO categories (nome) VALUES (?)",
                           [('Alimentação',), ('Transporte',), ('Lazer',), ('Outros',)])
        # Insere salário padrão
        sal = db.execute("SELECT COUNT(*) FROM settings WHERE chave='salario_mes'").fetchone()[0]
        if sal == 0:
            db.execute("INSERT INTO settings (chave, valor) VALUES ('salario_mes', 0)")
        db.commit()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def converter_valor(valor_str):
    """Converte 2.700,50 ou 2700,50 ou 2700.50 para float"""
    valor_str = valor_str.strip()
    valor_str = valor_str.replace('.', '').replace(',', '.')
    return float(valor_str)

@app.route("/", methods=["GET"])
def index():
    db = get_db()
    categories = db.execute("SELECT * FROM categories").fetchall()
    salario = db.execute("SELECT valor FROM settings WHERE chave='salario_mes'").fetchone()[0]
    transactions = db.execute("""
        SELECT t.*, c.nome as categoria_nome FROM transactions t
        JOIN categories c ON t.categoria_id = c.id
        ORDER BY t.data DESC LIMIT 10
    """).fetchall()
    total_gasto = db.execute("SELECT SUM(valor) FROM transactions").fetchone()[0] or 0
    saldo = salario - total_gasto
    return render_template("index.html", categories=categories, salario=salario,
                           transactions=transactions, total_gasto=total_gasto, saldo=saldo)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario_str = request.form.get("salario", "")
        salario = converter_valor(salario_str)
        db = get_db()
        db.execute("UPDATE settings SET valor =? WHERE chave='salario_mes'", (salario,))
        db.execute("DELETE FROM transactions")
        db.commit()
        flash(f"Salário de R$ {salario:.2f} definido! Lançamentos zerados.", "success")
    except Exception as e:
        flash(f"Erro: Valor inválido. Use 2700 ou 2.700,50", "error")
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    try:
        categoria_id = int(request.form["categoria_id"])
        valor = converter_valor(request.form["valor"])
        descricao = request.form.get("descricao", "")
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = get_db()
        db.execute("INSERT INTO transactions (categoria_id, valor, descricao, data) VALUES (?,?,?,?)",
                   (categoria_id, valor, descricao, data))
        db.commit()
        flash("Gasto lançado com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao lançar: Preencha categoria e valor corretamente", "error")
    return redirect(url_for("index"))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
