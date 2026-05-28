import os
import re
import csv
import io
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, make_response
from werkzeug.security import check_password_hash, generate_password_hash

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
# O Flask busca a chave do arquivo oculto, e não mais do texto aberto
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# ==========================================
# CONEXÃO COM O BANCO DE DADOS MYSQL
# ==========================================
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'sistema_financeiro')
    )

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def validar_cpf_cnpj(documento):
    # Remove qualquer coisa que não seja número (pontos, traços, espaços)
    doc = re.sub(r'[^0-9]', '', str(documento))
    
    # VALIDAÇÃO DE CPF (11 dígitos)
    if len(doc) == 11:
        if doc == doc[0] * 11: return False
        
        soma = sum(int(doc[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        
        soma = sum(int(doc[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        
        return str(digito1) == doc[9] and str(digito2) == doc[10]
        
    # VALIDAÇÃO DE CNPJ (14 dígitos)
    elif len(doc) == 14:
        if doc == doc[0] * 14: return False
        
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(doc[i]) * pesos1[i] for i in range(12))
        digito1 = 11 - (soma % 11) if soma % 11 >= 2 else 0
        
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(doc[i]) * pesos2[i] for i in range(13))
        digito2 = 11 - (soma % 11) if soma % 11 >= 2 else 0
        
        return str(digito1) == doc[12] and str(digito2) == doc[13]
        
    return False

# ==========================================
# ROTAS DE AUTENTICAÇÃO E PÁGINA INICIAL
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        cpf_cnpj = request.form['cpf_cnpj']
        usuario_digitado = request.form['usuario']
        senha_digitada = request.form['senha']
        
        if not validar_cpf_cnpj(cpf_cnpj):
            flash('Erro: O CPF ou CNPJ digitado é inválido. Verifique os números.')
            return redirect(url_for('cadastro'))

        senha_criptografada = generate_password_hash(senha_digitada)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # MySQL usa %s em vez de ?
            cursor.execute('''
                INSERT INTO usuarios (nome, email, cpf_cnpj, usuario, senha) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (nome, email, cpf_cnpj, usuario_digitado, senha_criptografada))
            conn.commit()
            flash('Cadastro realizado com sucesso! Faça o seu login.')
            return redirect(url_for('login'))
        except mysql.connector.errors.IntegrityError:
            flash('Erro: Esse Usuário, E-mail ou CPF/CNPJ já estão cadastrados.')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form['usuario'] 
        senha_digitada = request.form['senha']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # MySQL usa %s
        cursor.execute('SELECT * FROM usuarios WHERE usuario = %s OR cpf_cnpj = %s', (identificador, identificador))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()

        if user and check_password_hash(user['senha'], senha_digitada):
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais incorretas! Tente novamente.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ==========================================
# ROTAS DO SISTEMA (DASHBOARD E CRUD)
# ==========================================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    mes_atual = datetime.now().strftime('%m')
    ano_atual = datetime.now().strftime('%Y')
    
    mes_filtro = request.args.get('mes', mes_atual)
    ano_filtro = request.args.get('ano', ano_atual)
    
    busca_data = f"{ano_filtro}-{mes_filtro}%"

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # MYSQL usa %s
    cursor.execute('''
        SELECT SUM(valor) FROM transacoes 
        WHERE usuario_id = %s AND tipo = 'Receita' AND data LIKE %s
    ''', (user_id, busca_data))
    receitas = cursor.fetchone()[0] or 0.0

    cursor.execute('''
        SELECT SUM(valor) FROM transacoes 
        WHERE usuario_id = %s AND tipo = 'Despesa' AND data LIKE %s
    ''', (user_id, busca_data))
    despesas = cursor.fetchone()[0] or 0.0
    
    cursor.close()
    conn.close()
    
    # Convertendo para float porque o Decimal do MySQL pode causar erro na soma com 0.0
    saldo = float(receitas) - float(despesas)
    
    return render_template('dashboard.html', 
                           receitas=float(receitas), 
                           despesas=float(despesas), 
                           saldo=saldo,
                           mes_filtro=mes_filtro,
                           ano_filtro=ano_filtro)

@app.route('/transacoes', methods=['GET', 'POST'])
def transacoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = request.form['valor']
        categoria = request.form['categoria']
        tipo = request.form['tipo']
        data = request.form['data']
        usuario_id = session['user_id']
        
        cursor.execute('''
            INSERT INTO transacoes (descricao, valor, categoria, tipo, data, usuario_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (descricao, valor, categoria, tipo, data, usuario_id))
        conn.commit()
        return redirect(url_for('transacoes'))
        
    cursor.execute('SELECT * FROM transacoes WHERE usuario_id = %s ORDER BY data DESC', (session['user_id'],))
    lista_transacoes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('transacoes.html', transacoes=lista_transacoes)

@app.route('/deletar/<int:id>')
def deletar(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transacoes WHERE id = %s AND usuario_id = %s', (id, session['user_id']))
    conn.commit()
    
    cursor.close()
    conn.close()
    return redirect(url_for('transacoes'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = request.form['valor']
        categoria = request.form['categoria']
        tipo = request.form['tipo']
        data = request.form['data']
        
        cursor.execute('''
            UPDATE transacoes 
            SET descricao = %s, valor = %s, categoria = %s, tipo = %s, data = %s
            WHERE id = %s AND usuario_id = %s
        ''', (descricao, valor, categoria, tipo, data, id, session['user_id']))
        conn.commit()
        
        cursor.close()
        conn.close()
        return redirect(url_for('transacoes'))
        
    cursor.execute('SELECT * FROM transacoes WHERE id = %s AND usuario_id = %s', (id, session['user_id']))
    transacao = cursor.fetchone()
    
    cursor.close()
    conn.close()
    return render_template('editar.html', transacao=transacao)

# Mantendo as duas rotas de exportação do seu código para garantir que tudo funcione
@app.route('/exportar_csv')
def exportar_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id'] 
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM transacoes WHERE usuario_id = %s', (user_id,))
    transacoes = cursor.fetchall()
    
    cursor.close()
    conn.close()

    def generate():
        data = ['Data', 'Descricao', 'Categoria', 'Tipo', 'Valor']
        yield ','.join(data) + '\n'
        
        for t in transacoes:
            linha = [
                str(t['data']), 
                str(t['descricao']), 
                str(t['categoria']), 
                str(t['tipo']), 
                str(t['valor'])
            ]
            yield ','.join(linha) + '\n'

    return Response(
        generate(), 
        mimetype='text/csv', 
        headers={"Content-Disposition": "attachment;filename=relatorio_financeiro.csv"}
    )

@app.route('/exportar')
def exportar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM transacoes WHERE usuario_id = %s ORDER BY data DESC', (session['user_id'],))
    transacoes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor (R$)'])
    
    for t in transacoes:
        cw.writerow([t['data'], t['descricao'], t['categoria'], t['tipo'], str(t['valor']).replace('.', ',')])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=meu_relatorio_financeiro.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    
    return output

@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    user_id = session['user_id']
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        nova_senha = request.form['nova_senha']
        
        if nova_senha.strip():
            senha_criptografada = generate_password_hash(nova_senha)
            cursor.execute('''
                UPDATE usuarios SET nome = %s, email = %s, senha = %s WHERE id = %s
            ''', (nome, email, senha_criptografada, user_id))
        else:
            cursor.execute('''
                UPDATE usuarios SET nome = %s, email = %s WHERE id = %s
            ''', (nome, email, user_id))
            
        conn.commit()
        flash('Configurações salvas com sucesso!')
        return redirect(url_for('configuracoes'))
        
    cursor.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    usuario = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('configuracoes.html', usuario=usuario)

if __name__ == '__main__':
    app.run(debug=True)