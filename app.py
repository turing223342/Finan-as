from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from datetime import datetime
import sqlite3
from openpyxl import Workbook
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "chave_super_secreta_2025"

DB_DIR = "/var/data" if os.path.isdir("/var/data") else os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(DB_DIR, "ajuda_custo.db")

CATEGORIAS = {'💊 Essenciais': 50, '📈 Ativos': 25, '🏦 Estabilidade': 15, '🎮 Lazer': 10}

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, usuario TEXT UNIQUE, senha TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS settings (user_id INT, chave TEXT, valor REAL, PRIMARY KEY(user_id,chave))')
    db.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, user_id INT, categoria TEXT, valor REAL, descricao TEXT, data TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, user_id INT, categoria TEXT, valor_meta REAL)')
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        senha_hash = generate_password_hash("1234")
        db.execute("INSERT INTO users (usuario, senha) VALUES (?,?)", ("admin", senha_hash))
    db.commit(); db.close()

def converter_valor(v):
    try: return float(str(v).strip().replace('.', '').replace(',', '.'))
    except: return 0

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        db = sqlite3.connect(DATABASE)
        user = db.execute("SELECT * FROM users WHERE usuario=?", (request.form["usuario"],)).fetchone()
        if user and check_password_hash(user[2], request.form["senha"]):
            session["user_id"] = user[0]; db.close()
            return redirect(url_for("index"))
        flash("Usuário ou senha inválidos", "error"); db.close()
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.route("/")
def index():
    if "user_id" not in session: return redirect(url_for("login"))
    init_db(); user_id = session["user_id"]
    db = sqlite3.connect(DATABASE); db.row_factory = sqlite3.Row
    salario_total = db.execute("SELECT valor FROM settings WHERE user_id=? AND chave='salario_total'", (user_id,)).fetchone()
    salario_total = salario_total[0] if salario_total else 0
    total_gasto = db.execute("SELECT SUM(valor) FROM gastos WHERE user_id=?", (user_id,)).fetchone()[0] or 0
    historico = db.execute("SELECT * FROM gastos WHERE user_id=? ORDER BY data DESC LIMIT 10", (user_id,)).fetchall()
    categorias = []
    for nome, perc in CATEGORIAS.items():
        definido = salario_total * (perc / 100)
        gasto = db.execute("SELECT SUM(valor) FROM gastos WHERE user_id=? AND categoria=?", (user_id,nome)).fetchone()[0] or 0
        saldo = definido - gasto
        meta = db.execute("SELECT valor_meta FROM metas WHERE user_id=? AND categoria=?", (user_id,nome)).fetchone()
        meta_valor = meta[0] if meta else 0
        progresso_meta = int((saldo/meta_valor*100)) if meta_valor>0 else 0
        categorias.append({'nome': nome, 'percentual': perc, 'definido': definido, 'gasto': gasto, 'saldo': saldo, 'estourou': saldo<0, 'meta': meta_valor, 'progresso_meta': progresso_meta})
    db.close()
    return render_template("index.html", categorias=categorias, salario_total=salario_total, total_gasto=total_gasto, historico=historico)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    if "user_id" not in session: return redirect(url_for("login"))
    salario = converter_valor(request.form["salario"])
    db = sqlite3.connect(DATABASE)
    db.execute("INSERT OR REPLACE INTO settings (user_id, chave, valor) VALUES (?,?,?)", (session["user_id"],'salario_total',salario))
    db.execute("DELETE FROM gastos WHERE user_id=?", (session["user_id"],))
    db.commit(); db.close()
    flash(f"Salário R$ {salario:.2f} definido!", "success")
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    if "user_id" not in session: return redirect(url_for("login"))
    valor = converter_valor(request.form["valor"])
    db = sqlite3.connect(DATABASE)
    db.execute("INSERT INTO gastos (user_id, categoria, valor, descricao, data) VALUES (?,?,?,?,?)", (session["user_id"], request.form["categoria"], valor, request.form.get("descricao", ""), datetime.now().strftime("%d/%m %H:%M")))
    db.commit(); db.close()
    flash("Gasto lançado!", "success")
    return redirect(url_for("index"))

@app.route("/meta", methods=["POST"])
def meta():
    if "user_id" not in session: return redirect(url_for("login"))
    db = sqlite3.connect(DATABASE)
    db.execute("INSERT OR REPLACE INTO metas (user_id, categoria, valor_meta) VALUES (?,?,?)", (session["user_id"], request.form["categoria"], converter_valor(request.form["valor_meta"])))
    db.commit(); db.close()
    flash("Meta salva!", "success")
    return redirect(url_for("index"))

@app.route("/exportar")
def exportar():
    if "user_id" not in session: return redirect(url_for("login"))
    db = sqlite3.connect(DATABASE)
    gastos = db.execute("SELECT data,categoria,descricao,valor FROM gastos WHERE user_id=?", (session["user_id"],)).fetchall()
    wb = Workbook(); ws = wb.active; ws.title = "Gastos"
    ws.append(["Data","Categoria","Descrição","Valor"])
    for g in gastos: ws.append(list(g))
    arquivo = os.path.join(DB_DIR, "gastos.xlsx"); wb.save(arquivo)
    return send_file(arquivo, as_attachment=True)

from werkzeug.exceptions import MethodNotAllowed

@app.errorhandler(405)
def handle_405(e):
    # Se o erro 405 for em /login, responde 204 pra calar o bot. Senão mostra erro normal
    if request.path == "/login" and request.method == "POST":
        return "", 204
    return "Method Not Allowed", 405

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
