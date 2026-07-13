def converter_valor(valor_str):
    """Converte 2.700,50 ou 2700,50 ou 2700.50 para float"""
    valor_str = valor_str.replace('.', '').replace(',', '.') # tira ponto de milhar e troca virgula por ponto
    return float(valor_str)

@app.route("/lancar_salario", methods=["POST"])
def lancar_salario():
    try:
        salario_str = request.form["salario"]
        salario = converter_valor(salario_str) # <-- usa a nova função
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
        valor = converter_valor(valor_str) # <-- usa a nova função
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
