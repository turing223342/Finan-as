from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "chave_secreta_123"
DATABASE = 'ajuda_custo.db'
CATEGORIAS = {'Essenciais': 50, 'Ativos': 25, 'Estabilidade': 15, 'Lazer': 10}

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute('CREATE TABLE IF NOT EXISTS settings (chave TEXT PRIMARY KEY, valor REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, categoria TEXT, valor REAL, descricao TEXT, data TEXT)')
    if db.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        for cat in CATEGORIAS: db.execute("INSERT INTO settings VALUES (?,0)", (cat,))
    db.execute("INSERT OR IGNORE INTO settings VALUES ('salario_total',0)")
    db.commit(); db.close()

def converter_valor(v):
    return float(v.strip().replace('.', '').replace(',', '.'))

@app.route("/")
def index():
    init_db()
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    salario_total = db.execute("SELECT valor FROM settings WHERE chave='salario_total'").fetchone()[0]
    
    categorias = []
    for nome, perc in CATEGORIAS.items():
        definido = salario_total * (perc / 100)
        gasto = db.execute("SELECT SUM(valor) FROM gastos WHERE categoria=?", (nome,)).fetchone()[0] or 0
        saldo = definido - gasto
        categorias.append({'nome': nome, 'percentual': perc, 'definido': definido, 'gasto': gasto, 'saldo': saldo})
    db.close()
    return render_template("index.html", categorias=categorias)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario = converter_valor(request.form["salario"])
        db = sqlite3.connect(DATABASE)
        db.execute("UPDATE settings SET valor=? WHERE chave='salario_total'", (salario,))
        db.execute("DELETE FROM gastos") # zera os gastos do mês
        db.commit(); db.close()
        flash(f"Salário R$ {salario:.2f} definido e gastos zerados!", "success")
    except: flash("Valor inválido. Use 2700 ou 2.700,50", "error")
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    try:
        valor = converter_valor(request.form["valor"])
        categoria = request.form["categoria"]
        descricao = request.form.get("descricao", "")
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = sqlite3.connect(DATABASE)
        db.execute("INSERT INTO gastos (categoria, valor, descricao, data) VALUES (?,?,?,?)", (categoria, valor, descricao, data))
        db.commit(); db.close()
        flash(f"Gasto de R$ {valor:.2f} em {categoria} lançado!", "success")
    except: flash("Erro: Preencha categoria e valor", "error")
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=False)
