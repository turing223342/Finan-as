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
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Organizador Financeiro</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; background: #f5f5f5; }
  .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { padding: 10px; border-bottom: 1px solid #eee; }
  .negativo { color: #c62828; font-weight: bold; }
  .positivo { color: #2e7d32; }
  .badge-ruim { background: #ffebee; color: #c62828; padding: 4px 10px; border-radius: 12px; }
  .badge-ok { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 12px; }
  .badge-alerta { background: #fff8e1; color: #f57f17; padding: 4px 10px; border-radius: 12px; }
    input, select, button { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
    button { background: #1b5e20; color: #fff; border: 0; cursor: pointer; font-weight: bold; }
    button.secundario { background: #555; margin-top: 10px; }
  .flash-success { background: #e8f5e9; color: #2e7d32; padding: 12px; border-radius: 4px; }
  .flash-error { background: #ffebee; color: #c62828; padding: 12px; border-radius: 4px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .meta-input { width: 80px; display: inline-block; }
  </style>
</head>
<body>
  <h1>💰 Organizador Financeiro</h1>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for category, message in messages %}<div class="flash-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}
  {% endwith %}

  <div class="card">
    <h2>Resumo Geral</h2>
    <p><b>Entradas:</b> <span class="positivo">R$ {{ '%.2f'|format(total_entrada) }}</span></p>
    <p><b>Gastos:</b> <span class="negativo">R$ {{ '%.2f'|format(total_gasto) }}</span></p>
    <p><b>Saldo:</b> <span class="{{ 'negativo' if saldo_geral < 0 else 'positivo' }}">R$ {{ '%.2f'|format(saldo_geral) }}</span></p>
  </div>

  <div class="card">
    <h2>Editar Metas % <small style="font-weight:normal;">Total deve dar 100%</small></h2>
    <form method="post" action="{{ url_for('editar_metas') }}">
      {% for cat in categories %}
      <label>{{ cat["nome"] }}</label>
      <input class="meta-input" name="meta_{{ cat['id'] }}" type="number" value="{{ cat['percentual'] }}" min="0" max="100"> %
      {% endfor %}
      <button type="submit">Salvar Metas</button>
    </form>
  </div>

  <div class="card">
    <h2>Saldo por Categoria</h2>
    <table>
      <tr><th>Categoria</th><th>% Meta</th><th>Meta R$</th><th>Gasto Atual</th><th>Status</th></tr>
      {% for cat in categories %}
      <tr>
        <td>{{ cat["nome"] }}</td>
        <td>{{ cat["percentual"] }}%</td>
        <td>R$ {{ '%.2f'|format(meta_total * cat["percentual"] / 100) }}</td>
        <td class="negativo">R$ {{ '%.2f'|format(cat['gasto']) }}</td>
        <td>
          {% set meta = meta_total * cat["percentual"] / 100 %}
          {% if cat['gasto'] > meta %}<span class="badge-ruim">Estourou</span>
          {% elif cat['gasto'] > meta * 0.8 %}<span class="badge-alerta">Atenção</span>
          {% else %}<span class="badge-ok">OK</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
    {% if soma_metas!= 100 %}
      <p style="color:orange; margin-top:10px;"><b>Atenção:</b> A soma das metas está {{ soma_metas }}%. O ideal é 100%</p>
    {% endif %}
  </div>

  <div class="grid">
    <div class="card">
      <h2>Nova Transação</h2>
      <form method="post" action="{{ url_for('transacao') }}">
        <label>Tipo</label><select name="tipo" required><option value="entrada">Entrada</option><option value="gasto">Gasto</option></select>
        <label>Categoria</label><select name="categoria_id" required>{% for cat in categories %}<option value="{{ cat['id'] }}">{{ cat['nome'] }} - {{ cat['percentual'] }}%</option>{% endfor %}</select>
        <label>Valor R$</label><input name="valor" type="number" step="0.01" min="0.01" required>
        <label>Descrição</label><input name="descricao" type="text">
        <button type="submit">Salvar</button>
      </form>
    </div>
    <div class="card">
      <h2>Últimas 10 Movimentações</h2>
      <table><tr><th>Data</th><th>Categoria</th><th>Valor</th></tr>
      {% for tx in transactions %}<tr><td>{{ tx["data"][:10] }}</td><td>{{ tx["categoria_nome"] }}</td><td class="{{ 'negativo' if tx['valor'] < 0 else 'positivo' }}">R$ {{ '%.2f'|format(tx['valor']) }}</td></tr>{% endfor %}
      </table>
    </div>
  </div>
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

def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, nome TEXT, percentual INTEGER, saldo REAL DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, categoria_id INTEGER, tipo TEXT, valor REAL, descricao TEXT, data TEXT)")

    padrao = [("Essenciais", 50), ("Ativos", 25), ("Estabilidade", 15), ("Lazer", 10)]
    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        db.executemany("INSERT INTO categories (nome, percentual) VALUES (?,?)", padrao)
    db.commit()

with app.app_context():
    init_db()

@app.route("/")
def index():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    transactions = db.execute("SELECT t.*, c.nome AS categoria_nome FROM transactions t JOIN categories c ON t.categoria_id = c.id ORDER BY t.id DESC LIMIT 10").fetchall()
    total_entrada = db.execute("SELECT SUM(valor) FROM transactions WHERE valor > 0").fetchone()[0] or 0
    total_gasto = abs(db.execute("SELECT SUM(valor) FROM transactions WHERE valor < 0").fetchone()[0] or 0)
    saldo_geral = total_entrada - total_gasto
    soma_metas = sum([c['percentual'] for c in categories])

    categories_calc = []
    for cat in categories:
        gasto_cat = abs(db.execute("SELECT SUM(valor) FROM transactions WHERE categoria_id =? AND valor < 0", (cat["id"],)).fetchone()[0] or 0)
        categories_calc.append({**cat, "gasto": gasto_cat})

    return render_template_string(HTML, categories=categories_calc, transactions=transactions,
                                  total_entrada=total_entrada, total_gasto=total_gasto,
                                  saldo_geral=saldo_geral, meta_total=total_entrada, soma_metas=soma_metas)

@app.route("/transacao", methods=["POST"])
def transacao():
    try:
        tipo = request.form["tipo"]
        categoria_id = int(request.form["categoria_id"])
        valor = float(request.form["valor"])
        descricao = request.form.get("descricao", "")
    except:
        flash("Dados inválidos", "error")
        return redirect(url_for("index"))

    valor_db = -abs(valor) if tipo == "gasto" else abs(valor)
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute("INSERT INTO transactions (categoria_id, tipo, valor, descricao, data) VALUES (?,?,?,?,?)", (categoria_id, tipo, valor_db, descricao, data))
    db.execute("UPDATE categories SET saldo = saldo +? WHERE id =?", (valor_db, categoria_id))
    db.commit()
    flash("Transação salva!", "success")
    return redirect(url_for("index"))

@app.route("/editar_metas", methods=["POST"])
def editar_metas():
    db = get_db()
    soma = 0
    categories = db.execute("SELECT id FROM categories").fetchall()

    for cat in categories:
        nova_meta = int(request.form.get(f"meta_{cat['id']}", 0))
        soma += nova_meta
        db.execute("UPDATE categories SET percentual =? WHERE id =?", (nova_meta, cat['id']))

    db.commit()

    if soma!= 100:
        flash(f"Metas salvas! Mas a soma deu {soma}%. O ideal é 100%", "error")
    else:
        flash("Metas atualizadas com sucesso!", "success")

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troca-essa-chave-em-producao")

# Banco: usa /var/data no Render, ou pasta local
DB_DIR = "/var/data" if os.path.isdir("/var/data") else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "financas.db")

HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Organizador Financeiro 50/25/15/10</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; background: #f5f5f5; }
   .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1 { color: #1b5e20; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
   .negativo { color: #c62828; font-weight: bold; }
   .positivo { color: #2e7d32; }
   .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; }
   .badge-ruim { background: #ffebee; color: #c62828; }
   .badge-ok { background: #e8f5e9; color: #2e7d32; }
   .badge-alerta { background: #fff8e1; color: #f57f17; }
    input, select, button { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
    button { background: #1b5e20; color: #fff; border: 0; cursor: pointer; font-weight: bold; }
    button:hover { background: #114214; }
   .flash { padding: 12px; border-radius: 4px; margin-bottom: 15px; }
   .flash-success { background: #e8f5e9; color: #2e7d32; }
   .flash-error { background: #ffebee; color: #c62828; }
   .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media(max-width: 700px){.grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>💰 Organizador Financeiro</h1>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="flash flash-{{ category }}">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class="card">
    <h2>Resumo Geral</h2>
    <p><b>Entradas:</b> <span class="positivo">R$ {{ '%.2f'|format(total_entrada) }}</span></p>
    <p><b>Gastos:</b> <span class="negativo">R$ {{ '%.2f'|format(total_gasto) }}</span></p>
    <p><b>Saldo:</b> <span class="{{ 'negativo' if saldo_geral < 0 else 'positivo' }}">R$ {{ '%.2f'|format(saldo_geral) }}</span></p>
  </div>

  <div class="card">
    <h2>Saldo por Categoria - Regra 50/25/15/10</h2>
    <table>
      <tr><th>Categoria</th><th>%</th><th>Meta do Mês</th><th>Gasto Atual</th><th>Status</th></tr>
      {% for cat in categories %}
      <tr>
        <td>{{ cat["nome"] }}</td>
        <td>{{ cat["percentual"] }}%</td>
        <td>R$ {{ '%.2f'|format(meta_total * cat["percentual"] / 100) }}</td>
        <td class="{{ 'negativo' if cat['gasto'] > 0 else '' }}">R$ {{ '%.2f'|format(cat['gasto']) }}</td>
        <td>
          {% if cat['gasto'] > meta_total * cat["percentual"] / 100 %}
            <span class="badge badge-ruim">Estourou</span>
          {% elif cat['gasto'] > meta_total * cat["percentual"] / 100 * 0.8 %}
            <span class="badge badge-alerta">Atenção</span>
          {% else %}
            <span class="badge badge-ok">OK</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Nova Transação</h2>
      <form method="post" action="{{ url_for('transacao') }}">
        <label>Tipo</label>
        <select name="tipo" required><option value="entrada">Entrada</option><option value="gasto">Gasto</option></select>

        <label>Categoria</label>
        <select name="categoria_id" required>{% for cat in categories %}<option value="{{ cat['id'] }}">{{ cat['nome'] }}</option>{% endfor %}</select>

        <label>Valor R$</label><input name="valor" type="number" step="0.01" min="0.01" required>

        <label>Descrição</label><input name="descricao" type="text" placeholder="Ex: Supermercado">

        <button type="submit">Salvar</button>
      </form>
    </div>

    <div class="card">
      <h2>Últimas Movimentações</h2>
      <table>
        <tr><th>Data</th><th>Categoria</th><th>Valor</th></tr>
        {% for tx in transactions %}
        <tr>
          <td>{{ tx["data"][:10] }}</td>
          <td>{{ tx["categoria_nome"] }}</td>
          <td class="{{ 'negativo' if tx['valor'] < 0 else 'positivo' }}">R$ {{ '%.2f'|format(tx['valor']) }}</td>
        </tr>
        {% endfor %}
      </table>
    </div>
  </div>
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
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, nome TEXT NOT NULL, percentual INTEGER NOT NULL, saldo REAL NOT NULL DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, categoria_id INTEGER, tipo TEXT, valor REAL, descricao TEXT, data TEXT, FOREIGN KEY(categoria_id) REFERENCES categories(id))")

    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        padrao = [("Essenciais", 50), ("Ativos", 25), ("Estabilidade", 15), ("Lazer", 10)]
        db.executemany("INSERT INTO categories (nome, percentual) VALUES (?,?)", padrao)
    db.commit()

with app.app_context():
    init_db()

@app.route("/")
def index():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    transactions = db.execute("SELECT t.*, c.nome AS categoria_nome FROM transactions t JOIN categories c ON t.categoria_id = c.id ORDER BY t.id DESC LIMIT 10").fetchall()

    total_entrada = db.execute("SELECT SUM(valor) FROM transactions WHERE valor > 0").fetchone()[0] or 0
    total_gasto = abs(db.execute("SELECT SUM(valor) FROM transactions WHERE valor < 0").fetchone()[0] or 0)
    saldo_geral = total_entrada - total_gasto

    categories_calc = []
    for cat in categories:
        gasto_cat = abs(db.execute("SELECT SUM(valor) FROM transactions WHERE categoria_id =? AND valor < 0", (cat["id"],)).fetchone()[0] or 0)
        categories_calc.append({**cat, "gasto": gasto_cat})

    return render_template_string(HTML, categories=categories_calc, transactions=transactions,
                                  total_entrada=total_entrada, total_gasto=total_gasto,
                                  saldo_geral=saldo_geral, meta_total=total_entrada)

@app.route("/transacao", methods=["POST"])
def transacao():
    try:
        tipo = request.form["tipo"]
        categoria_id = int(request.form["categoria_id"])
        valor = float(request.form["valor"])
        descricao = request.form.get("descricao", "")
    except:
        flash("Erro: Dados inválidos", "error")
        return redirect(url_for("index"))

    if valor <= 0:
        flash("Erro: Valor deve ser maior que zero", "error")
        return redirect(url_for("index"))

    valor_db = -abs(valor) if tipo == "gasto" else abs(valor)
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    db.execute("INSERT INTO transactions (categoria_id, tipo, valor, descricao, data) VALUES (?,?,?,?,?)",
               (categoria_id, tipo, valor_db, descricao, data))
    db.execute("UPDATE categories SET saldo = saldo +? WHERE id =?", (valor_db, categoria_id))
    db.commit()
    flash("Transação salva!", "success")
    return redirect(url_for("index"))

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
