import os
import sqlite3
from datetime import datetime

from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

# Caminho do banco: usa /var/data se existir (disco persistente do Render),
# caso contrário salva no diretório do projeto.
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
    body { font-family: Arial, sans-serif; max-width: 760px; margin: 24px auto; padding: 0 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { padding: 8px; border: 1px solid #ddd; text-align: left; }
    .negativo { color: #b71c1c; font-weight: bold; }
    .positivo { color: #1b5e20; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 0.9rem; }
    .badge-declinio { background: #fdecea; color: #b71c1c; }
    .badge-ok { background: #e8f5e9; color: #1b5e20; }
    form { margin-top: 24px; }
    label { display: block; margin-top: 10px; }
    input, select, button { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; }
    button { background: #1b5e20; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }
    button:hover { background: #164d1a; }
  </style>
</head>
<body>
  <h1>Organizador Financeiro</h1>

  <section>
    <h2>Saldo por categoria</h2>
    <table>
      <tr>
        <th>Categoria</th>
        <th>%</th>
        <th>Saldo</th>
        <th>Status</th>
      </tr>
      {% for cat in categories %}
      <tr>
        <td>{{ cat["nome"] }}</td>
        <td>{{ cat["percentual"] }}%</td>
        <td class="{{ 'negativo' if cat['saldo'] < 0 else 'positivo' }}">
          R$ {{ '%.2f'|format(cat['saldo']) }}
        </td>
        <td>
          {% if cat['saldo'] < 0 %}
            <span class="badge badge-declinio">Negativo</span>
          {% else %}
            <span class="badge badge-ok">OK</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
  </section>

  <section>
    <h2>Registrar entrada ou gasto</h2>
    <form method="post" action="{{ url_for('transacao') }}">
      <label>Tipo</label>
      <select name="tipo" required>
        <option value="entrada">Entrada</option>
        <option value="gasto">Gasto</option>
      </select>

      <label>Categoria</label>
      <select name="categoria_id" required>
        {% for cat in categories %}
          <option value="{{ cat['id'] }}">{{ cat['nome'] }} ({{ cat['percentual'] }}%)</option>
        {% endfor %}
      </select>

      <label>Valor</label>
      <input name="valor" type="number" step="0.01" min="0.01" placeholder="1500.00" required>

      <label>Descrição</label>
      <input name="descricao" type="text" placeholder="Ex: Conta de luz">

      <button type="submit">Salvar</button>
    </form>
  </section>

  <section>
    <h2>Últimas transações</h2>
    <table>
      <tr><th>Data</th><th>Tipo</th><th>Categoria</th><th>Valor</th><th>Descrição</th></tr>
      {% for tx in transactions %}
      <tr>
        <td>{{ tx["data"] }}</td>
        <td>{{ tx["tipo"] }}</td>
        <td>{{ tx["categoria_nome"] }}</td>
        <td class="{{ 'negativo' if tx['valor'] < 0 else 'positivo' }}">
          {{ 'R$ %.2f'|format(tx['valor']) }}
        </td>
        <td>{{ tx["descricao"] }}</td>
      </tr>
      {% endfor %}
    </table>
  </section>
</body>
</html>
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        percentual INTEGER NOT NULL,
        saldo REAL NOT NULL DEFAULT 0
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        valor REAL NOT NULL,
        descricao TEXT,
        data TEXT NOT NULL,
        FOREIGN KEY(categoria_id) REFERENCES categories(id)
    )
    """)
    conn.commit()

    categorias = conn.execute("SELECT COUNT(*) AS cnt FROM categories").fetchone()["cnt"]
    if categorias == 0:
        conn.executemany(
            "INSERT INTO categories (nome, percentual, saldo) VALUES (?, ?, ?)",
            [
                ("Reserva de emergência", 25, 0),
                ("Investimentos", 50, 0),
                ("Lazer", 15, 0),
                ("Reconpensas", 10, 0),
            ],
        )
        conn.commit()
    conn.close()


# Inicializa o banco no import (funciona tanto com "python app.py"
# quanto com gunicorn em produção).
init_db()


@app.route("/")
def index():
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    transactions = conn.execute("""
        SELECT t.*, c.nome AS categoria_nome
        FROM transactions t
        JOIN categories c ON t.categoria_id = c.id
        ORDER BY t.id DESC
        LIMIT 10
    """).fetchall()
    conn.close()
    return render_template_string(HTML, categories=categories, transactions=transactions)


@app.route("/transacao", methods=["POST"])
def transacao():
    tipo = request.form.get("tipo", "").strip()
    if tipo not in ("entrada", "gasto"):
        return "Tipo inválido", 400

    try:
        categoria_id = int(request.form["categoria_id"])
        valor = float(request.form["valor"])
    except (KeyError, ValueError):
        return "Dados inválidos", 400

    if valor <= 0:
        return "Valor deve ser maior que zero", 400

    descricao = request.form.get("descricao", "").strip()
    valor = -abs(valor) if tipo == "gasto" else abs(valor)

    conn = get_db()
    # Garante que a categoria existe
    cat = conn.execute("SELECT id FROM categories WHERE id = ?", (categoria_id,)).fetchone()
    if not cat:
        conn.close()
        return "Categoria não encontrada", 400

    conn.execute(
        "INSERT INTO transactions (categoria_id, tipo, valor, descricao, data) VALUES (?, ?, ?, ?, ?)",
        (categoria_id, tipo, valor, descricao, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.execute(
        "UPDATE categories SET saldo = saldo + ? WHERE id = ?",
        (valor, categoria_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
