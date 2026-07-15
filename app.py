from flask import Flask, request, redirect, url_for, render_template_string, flash, send_file
import sqlite3
from datetime import datetime, timedelta
import io
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "finanas2025"
DATABASE = 'ajuda_custo.db'

CATEGORIAS = {'💊 Essenciais': 50, '📈 Ativos': 25, '🏦 Estabilidade': 15, '🎮 Lazer': 10}

HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Finan-as V3.1</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:'Segoe UI',Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);margin:0;padding:20px;min-height:100vh;color:#333}
.container{max-width:1200px;margin:0 auto}
.header{background:white;padding:25px;border-radius:15px;margin-bottom:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2);text-align:center}
.header h1{margin:0;color:#667eea;font-size:32px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-bottom:20px}
.card{background:white;padding:25px;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}
.card h3{margin:0 0 15px 0;font-size:20px;color:#667eea}
.saldo{font-size:28px;font-weight:bold;color:#667eea;margin:10px 0}
.progresso{background:#eee;height:12px;border-radius:10px;overflow:hidden;margin:15px 0}
.barra{background:linear-gradient(90deg,#667eea,#764ba2);height:100%;transition:width 0.3s}
.alert{color:#e74c3c;font-weight:bold}
.btn{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:12px 25px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin:5px;text-decoration:none;display:inline-block}
.btn:hover{opacity:0.9}
input{padding:10px;border:2px solid #ddd;border-radius:8px;width:120px;margin:5px}
.flash{padding:15px;background:#d4edda;color:#155724;border-radius:8px;margin-bottom:15px;text-align:center}
.salario-box{background:white;padding:20px;border-radius:15px;margin-bottom:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}
.historico{background:white;padding:20px;border-radius:15px;margin-bottom:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}
table{width:100%;border-collapse:collapse}
td,th{padding:10px;border-bottom:1px solid #eee;text-align:left}
canvas{max-width:400px;margin:20px auto}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 Finan-as V3.1</h1>
<p>Saldo Total: <b>R$ {{ "%.2f"|format(salario_total - total_gasto) }}</b></p>
<a href="/exportar" class="btn">📥 Baixar Excel</a>
</div>

{% with messages = get_flashed_messages() %}
{% if messages %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}

<div class="salario-box">
<h3>💰 Lançar Salário do Mês</h3>
<form method="POST" action="/salario">
<input type="text" name="salario" placeholder="Ex: 5000,00" required>
<button class="btn" type="submit">Definir Salário</button>
<a href="/zerar" class="btn" style="background:#e74c3c" onclick="return confirm('Tem certeza que quer zerar o mês?')">🔄 Zerar Mês</a>
</form>
</div>

<div class="cards">
{% for cat in categorias %}
<div class="card">
<h3>{{ cat.nome }}</h3>
<p><b>{{ cat.percentual }}%</b> do salário</p>
<p>Definido: R$ {{ "%.2f"|format(cat.definido) }}</p>
<p>Gasto: R$ {{ "%.2f"|format(cat.gasto) }}</p>
<p class="saldo">Saldo: R$ {{ "%.2f"|format(cat.saldo) }}</p>
{% if cat.estourou %}<p class="alert">⚠️ ESTOUROU!</p>{% endif %}
<div class="progresso"><div class="barra" style="width:{{ cat.percentual_gasto }}%"></div></div>
<form method="POST" action="/gasto">
<input type="hidden" name="categoria" value="{{ cat.nome }}">
<input type="text" name="valor" placeholder="R$ 0,00" required>
<input type="text" name="descricao" placeholder="Descrição">
<button class="btn" type="submit">Lançar</button>
</form>
</div>
{% endfor %}
</div>

<div class="card">
<h3>📊 Gráfico de Gastos</h3>
<canvas id="grafico"></canvas>
</div>

<div class="historico">
<h3>📜 Histórico do Mês</h3>
<table>
<tr><th>Data</th><th>Categoria</th><th>Descrição</th><th>Valor</th></tr>
{% for g in historico %}
<tr>
<td>{{ g.data }}</td>
<td>{{ g.categoria }}</td>
<td>{{ g.descricao }}</td>
<td>R$ {{ "%.2f"|format(g.valor) }}</td>
</tr>
{% endfor %}
</table>
</div>

</div>
<script>
const ctx = document.getElementById('grafico');
new Chart(ctx, {
type: 'pie',
data: {
labels: {{ labels|tojson }},
datasets: [{
data: {{ dados|tojson }},
backgroundColor: ['#667eea','#764ba2','#f093fb','#f5576c']
}]
}
});
</script>
</body>
</html>
'''

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, categoria TEXT, valor REAL, descricao TEXT, data TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS config (chave TEXT