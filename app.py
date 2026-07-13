from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "chave_secreta_123"
DATABASE = 'ajuda_custo.db'
CATEGORIAS = {'💊 Essenciais': 50, '📈 Ativos': 25, '🏦 Estabilidade': 15, '🎮 Lazer': 10}

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute('CREATE TABLE IF NOT EXISTS settings (chave TEXT PRIMARY KEY, valor REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, categoria TEXT, valor REAL, descricao TEXT, data TEXT)')
    if db.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        for cat in CATEGORIAS: db.execute("INSERT INTO settings VALUES (?,0)", (cat,))
    db.execute("INSERT OR IGNORE INTO settings VALUES ('salario_total',0)")
    db.commit(); db.close()

def converter_valor(v): return float(v.strip().replace('.', '').replace(',', '.'))

@app.route("/")
def index():
    init_db()
    db = sqlite3.connect(DATABASE); db.row_factory = sqlite3.Row
    salario_total = db.execute("SELECT valor FROM settings WHERE chave='salario_total'").fetchone()[0]
    total_gasto = db.execute("SELECT SUM(valor) FROM gastos").fetchone()[0] or 0
    historico = db.execute("SELECT * FROM gastos ORDER BY data DESC LIMIT 10").fetchall()
    
    categorias = []
    for nome, perc in CATEGORIAS.items():
        definido = salario_total * (perc / 100)
        gasto = db.execute("SELECT SUM(valor) FROM gastos WHERE categoria=?", (nome,)).fetchone()[0] or 0
        saldo = definido - gasto
        estourou = saldo < 0
        categorias.append({'nome': nome, 'percentual': perc, 'definido': definido, 'gasto': gasto, 'saldo': saldo, 'estourou': estourou})
    db.close()
    return render_template("index.html", categorias=categorias, salario_total=salario_total, total_gasto=total_gasto, historico=historico)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario = converter_valor(request.form["salario"])
        db = sqlite3.connect(DATABASE)
        db.execute("UPDATE settings SET valor=? WHERE chave='salario_total'", (salario,))
        db.execute("DELETE FROM gastos")
        db.commit(); db.close()
        flash(f"Salário R$ {salario:.2f} definido! Gastos zerados.", "success")
    except: flash("Valor inválido.", "error")
    return redirect(url_for("index"))

@app.route("/zerar_mes")
def zerar_mes():
    db = sqlite3.connect(DATABASE)
    db.execute("UPDATE settings SET valor=0 WHERE chave='salario_total'")
    db.execute("DELETE FROM gastos")
    db.commit(); db.close()
    flash("Mês zerado! Pode lançar um novo salário.", "success")
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    try:
        valor = converter_valor(request.form["valor"])
        categoria = request.form["categoria"]
        descricao = request.form.get("descricao", "")
        data = datetime.now().strftime("%d/%m %H:%M")
        db = sqlite3.connect(DATABASE)
        db.execute("INSERT INTO gastos (categoria, valor, descricao, data) VALUES (?,?,?,?)", (categoria, valor, descricao, data))
        db.commit(); db.close()
        flash(f"Gasto lançado!", "success")
    except: flash("Erro ao lançar gasto.", "error")
    return redirect(url_for("index"))

if __name__ == '__main__': app.run(debug=False)