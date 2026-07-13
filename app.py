import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troca-essa-chave-em-producao")

DB_DIR = "/var/data" if os.path.isdir("/var/data") else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "financas.db")

HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Organizador Financeiro 50/25/15/10</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; background: #f5f5f5; }
.card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1 { color: #1b5e20; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
.negativo { color: #c62828; font-weight: bold; }
.positivo { color: #2e7d32; }
.badge-ruim { background: #ffebee; color: #c62828; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
.badge-ok { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
.badge-alerta { background: #fff8e1; color: #f57f17; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
    input, select, button { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
    button { background: #1b5e20; color: #fff; border: 0; cursor: pointer; font-weight: bold; }
    button:hover { background: #114214; }
.flash-success { background: #e8f5e9; color: #2e7d32; padding: 12px; border-radius: 4px; margin-bottom: 15px; }
.flash-error { background: #ffebee; color: #c62828; padding: 12px; border-radius: 4px; margin-bottom: 15px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media(max-width: 700px){.grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>💰 Organizador Financeiro 50/25/15/10</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for category, message in messages %}<div class="flash-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}
  {% endwith %}
  {% if salario_mes == 0 %}
  <div class="card" style="border-left: 5px solid #1b5e20;">
    <h2>1. Lançar Salário do Mês</h2>
    <form method="post" action="{{ url_for('lancar_salario') }}">
      <label>Valor do Salário/Entrada do Mês. Ex: 2700 ou 2.700,50</label>
      <input name="salario" type="text" required placeholder="Ex: 2.700,00">
      <button type="submit">Dividir Automaticamente</button>
    </form>
  </div>
  {% else %}
  <div class="card">
    <h2>Salário do Mês: <span class="positivo">R$ {{ '%.2f'|format(salario_mes) }}</span>
      <a href="{{ url_for('resetar_mes') }}" style="font-size:12px; color:#c62828; float:right;">[Zerar Mês]</a>
    </h2>
  </div>
  {% endif %}
  <div class="card">
    <h2>Saldo por Categoria</h2>
    <table>
      <tr><th>Categoria</th><th>%</th><th>Valor Definido</th><th>Gasto</th><th>Saldo Restante</th><th>Status</th></tr>
      {% for cat in categories %}
      <tr>
        <td><b>{{ cat["nome"] }}</b></td>
        <td>{{ cat["percentual"] }}%</td>
        <td class="positivo">R$ {{ '%.2f'|format(cat["valor_definido"]) }}</td>
        <td class="negativo">R$ {{ '%.2f'|format(cat['gasto']) }}</td>
        <td class="{{ 'negativo' if cat['saldo_restante'] < 0 else 'positivo' }}">R$ {{ '%.2f'|format(cat['saldo_restante']) }}</td>
        <td>
          {% if cat['saldo_restante'] < 0 %}<span class="badge-ruim">Estourou</span>
          {% elif cat['saldo_restante'] < cat["valor_definido"] * 0.2 %}<span class="badge-alerta">Atenção</span>
          {% else %}<span class="badge-ok">OK</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% if salario_mes > 0 %}
  <div class="grid">
    <div class="card">
      <h2>2. Registrar Gasto</h2>
      <form method="post" action="{{ url_for('gasto') }}">
        <label>Categoria</label>
        <select name="categoria_id" required>
          {% for cat in categories %}
            <option value="{{ cat['id'] }}">{{ cat['nome'] }} - R$ {{ '%.2f'|format(cat['saldo_restante']) }} restante</option>
          {% endfor %}
        </select>
        <label>Valor do Gasto R$. Ex: 150 ou 1.250,99</label><input name="valor" type="text" required placeholder="Ex: 150,00">
        <label>Descrição</label><input name="descricao" type="text" placeholder="Ex: Supermercado">
        <button type="submit">Lançar Gasto</button>
      </form>
    </div>
    <div class="card">
      <h2>Últimos Gastos</h2>
      <table><tr><th>Data</th><th>Categoria</th><th>Valor</th></tr>
      {% for tx in transactions %}<tr><td>{{ tx["data"][:10] }}</td><td>{{ tx["categoria_nome"] }}</td><td class="negativo">R$ {{ '%.2f'|format(tx['valor']) }}</td></tr>{% endfor %}
      </table>
    </div>
  </div>
  {% endif %}
</body>
</html>
"""

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None: db.close()

def converter_valor(valor_str):
    valor_str = valor_str.replace('.', '').replace(',', '.')
    return float(valor_str)

def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS settings (chave TEXT PRIMARY KEY, valor REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, nome TEXT, percentual INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, categoria_id INTEGER, valor REAL, descricao TEXT, data TEXT)")
    padrao = [("Essenciais", 50), ("Ativos", 25), ("Estabilidade", 15), ("Lazer", 10)]
    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        db.executemany("INSERT INTO categories (nome, percentual) VALUES (?,?)", padrao)
    else:
        for i, (nome, perc) in enumerate(padrao):
            db.execute("UPDATE categories SET nome =?, percentual =? WHERE id =?", (nome, perc, i+1))
    if db.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        db.execute("INSERT INTO settings (chave, valor) VALUES ('salario_mes', 0)")
    db.commit()

with app.app_context():
    init_db()

@app.route("/", methods=["GET", "HEAD"])
def index():
    db = get_db()
    salario_mes = db.execute("SELECT valor FROM settings WHERE chave='salario_mes'").fetchone()['valor']
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    transactions = db.execute("SELECT t.*, c.nome AS categoria_nome FROM transactions t JOIN categories c ON t.categoria_id = c.id ORDER BY t.id DESC LIMIT 10").fetchall()
    categories_calc = []
    for cat in categories:
        valor_definido = salario_mes * cat["percentual"] / 100
        gasto = abs(db.execute("SELECT SUM(valor) FROM transactions WHERE categoria_id =?", (cat["id"],)).fetchone()[0] or 0)
        saldo_restante = valor_definido - gasto
        categories_calc.append({**cat, "valor_definido": valor_definido, "gasto": gasto, "saldo_restante": saldo_restante})
    return render_template_string(HTML, categories=categories_calc, transactions=transactions, salario_mes=salario_mes)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario_str = request.form["salario"]
        salario = converter_valor(salario_str)
    except:
        flash("Valor inválido. Use 2700 ou 2.700,50", "error")
        return redirect(url_for("index"))
    db = get_db()
    db.execute("UPDATE settings SET valor =? WHERE chave='salario_mes'", (salario,))
    db.execute("DELETE FROM transactions")
    db.commit()
    flash(f"Salário de R$ {salario:.2f} dividido com sucesso!", "success")
    return redirect(url_for("index"))

@app.route("/gasto", methods=["POST"])
def gasto():
    try:
        categoria_id = int(request.form["categoria_id"])
        valor_str = request.form["valor"]
        valor = converter_valor(valor_str)
        descricao = request.form.get("descricao", "")
    except:
        flash("Valor inválido. Use 2700 ou 2.700,50", "error")
        return redirect(url_for("index"))
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute("INSERT INTO transactions (categoria_id, valor, descricao, data) VALUES (?,?,?,?)", (categoria_id, valor, descricao, data))
    db.commit()
    flash("Gasto lançado!", "success")
    return redirect(url_for("index"))

@app.route("/resetar_mes")
def resetar_mes():
    db = get_db()
    db.execute("UPDATE settings SET valor = 0 WHERE chave='salario_mes'")
    db.execute("DELETE FROM transactions")
    db.commit()
    flash("Mês resetado! Pode lançar novo salário.", "success")
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"]) # <- CORRIGIDO AQUI
def login():
    flash("Esse app não tem login. Use direto na página inicial.", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
