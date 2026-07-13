from flask import Flask, render_template, request, redirect, url_for, flash, g
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "chave_secreta_troca_aqui"
DATABASE = 'ajuda_custo.db'

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, nome TEXT)''')
    db.execute('''CREATE TABLE IF NOT EXISTS settings (chave TEXT PRIMARY KEY, valor REAL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, categoria_id INTEGER, valor REAL, descricao TEXT, data TEXT)''')
    
    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        db.executemany("INSERT INTO categories (nome) VALUES (?)", [('Alimentação',), ('Transporte',), ('Lazer',), ('Outros',)])
    if db.execute("SELECT COUNT(*) FROM settings WHERE chave='salario_mes'").fetchone()[0] == 0:
        db.execute("INSERT INTO settings (chave, valor) VALUES ('salario_mes', 0)")
    db.commit()
    db.close()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

def converter_valor(valor_str):
    valor_str = valor_str.strip().replace('.', '').replace(',', '.')
    return float(valor_str)

@app.route("/")
def index():
    init_db() # <-- cria o banco toda vez que abrir
    db = get_db()
    categories = db.execute("SELECT * FROM categories").fetchall()
    salario = db.execute("SELECT valor FROM settings WHERE chave='salario_mes'").fetchone()[0]
    transactions = db.execute("SELECT t.*, c.nome as categoria_nome FROM transactions t JOIN categories c ON t.categoria_id = c.id ORDER BY t.data DESC LIMIT 10").fetchall()
    total_gasto = db.execute("SELECT SUM(valor) FROM transactions").fetchone()[0] or 0
    saldo = salario - total_gasto
    return render_template("index.html", categories=categories, salario=salario, transactions=transactions, total_gasto=total_gasto, saldo=saldo)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario = converter_valor(request.form["salario"])
        db = get_db()
        db.execute("UPDATE settings SET valor =? WHERE chave='salario_mes'", (salario,))
        db.execute("DELETE FROM transactions")
        db.commit()
        flash(f"Salário R$ {salario:.2f} definido!", "success")
    except: flash("Valor inválido. Use 2700 ou 2.700,50", "error")
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    try:
        valor = converter_valor(request.form["valor"])
        categoria_id = int(request.form["categoria_id"])
        descricao = request.form.get("descricao", "")
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = get_db()
        db.execute("INSERT INTO transactions (categoria_id, valor, descricao, data) VALUES (?,?,?,?)", (categoria_id, valor, descricao, data))
        db.commit()
        flash("Gasto lançado!", "success")
    except: flash("Erro: Preencha categoria e valor", "error")
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=False)
