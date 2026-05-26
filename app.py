from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import csv
import io
import re
import csv
from flask import Response

app = Flask(__name__)
app.secret_key = 'chave_secreta_tcc_joao' 

def get_db_connection():
    conn = sqlite3.connect('banco.db')
    conn.row_factory = sqlite3.Row 
    return conn


def validar_cpf_cnpj(documento):
    # Remove qualquer coisa que não seja número (pontos, traços, espaços)
    doc = re.sub(r'[^0-9]', '', str(documento))
    
    # VALIDAÇÃO DE CPF (11 dígitos)
    if len(doc) == 11:
        # Se for tudo o mesmo número (ex: 111.111.111-11), é inválido
        if doc == doc[0] * 11: return False
        
        # Cálculo do 1º dígito
        soma = sum(int(doc[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        
        # Cálculo do 2º dígito
        soma = sum(int(doc[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        
        return str(digito1) == doc[9] and str(digito2) == doc[10]
        
    # VALIDAÇÃO DE CNPJ (14 dígitos)
    elif len(doc) == 14:
        if doc == doc[0] * 14: return False
        
        # Cálculo do 1º dígito
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(doc[i]) * pesos1[i] for i in range(12))
        digito1 = 11 - (soma % 11) if soma % 11 >= 2 else 0
        
        # Cálculo do 2º dígito
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(doc[i]) * pesos2[i] for i in range(13))
        digito2 = 11 - (soma % 11) if soma % 11 >= 2 else 0
        
        return str(digito1) == doc[12] and str(digito2) == doc[13]
        
    # Se não tiver 11 nem 14 dígitos, é falso imediatamente
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
        
        # ========== NOVA VERIFICAÇÃO DE DOCUMENTO ==========
        if not validar_cpf_cnpj(cpf_cnpj):
            flash('Erro: O CPF ou CNPJ digitado é inválido. Verifique os números.')
            return redirect(url_for('cadastro'))
        # ===================================================

        senha_criptografada = generate_password_hash(senha_digitada)
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO usuarios (nome, email, cpf_cnpj, usuario, senha) 
                VALUES (?, ?, ?, ?, ?)
            ''', (nome, email, cpf_cnpj, usuario_digitado, senha_criptografada))
            conn.commit()
            flash('Cadastro realizado com sucesso! Faça o seu login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Erro: Esse Usuário ou CPF/CNPJ já estão cadastrados.')
        finally:
            conn.close()
            
    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 1. Capture o valor que vem do input no HTML (deve ter name="usuario")
        identificador = request.form['usuario'] 
        senha_digitada = request.form['senha']
        
        conn = get_db_connection()
        # 2. Agora o 'identificador' existe e pode ser usado aqui:
        user = conn.execute('SELECT * FROM usuarios WHERE usuario = ? OR cpf_cnpj = ?', (identificador, identificador)).fetchone()

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

@app.route('/exportar_csv')
def exportar_csv():
    # CORRIGIDO: Agora verifica 'user_id' igualzinho ao seu dashboard
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # CORRIGIDO: Usa a chave certa para pegar o ID do usuário logado
    user_id = session['user_id'] 
    
    conn = get_db_connection()
    transacoes = conn.execute('SELECT * FROM transacoes WHERE usuario_id = ?', (user_id,)).fetchall()
    conn.close()

    def generate():
        # Cabeçalho do arquivo Excel
        data = ['Data', 'Descricao', 'Categoria', 'Tipo', 'Valor']
        yield ','.join(data) + '\n'
        
        for t in transacoes:
            # Organiza as linhas pegando os dados do banco
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Pegamos o mês e o ano da URL. Se não tiver, usamos a data atual do computador.
    mes_atual = datetime.now().strftime('%m')
    ano_atual = datetime.now().strftime('%Y')
    
    mes_filtro = request.args.get('mes', mes_atual)
    ano_filtro = request.args.get('ano', ano_atual)
    
    # Criamos um padrão de busca para o banco de dados (ex: "2026-05%")
    busca_data = f"{ano_filtro}-{mes_filtro}%"

    conn = get_db_connection()
    
    # Agora a soma busca apenas transações que começam com o Ano e Mês escolhidos
    receitas = conn.execute('''
        SELECT SUM(valor) FROM transacoes 
        WHERE usuario_id = ? AND tipo = 'Receita' AND data LIKE ?
    ''', (user_id, busca_data)).fetchone()[0] or 0.0

    despesas = conn.execute('''
        SELECT SUM(valor) FROM transacoes 
        WHERE usuario_id = ? AND tipo = 'Despesa' AND data LIKE ?
    ''', (user_id, busca_data)).fetchone()[0] or 0.0
    
    conn.close()
    
    saldo = receitas - despesas
    
    # Passamos as variáveis de filtro para o HTML para sabermos o que está selecionado
    return render_template('dashboard.html', 
                           receitas=receitas, 
                           despesas=despesas, 
                           saldo=saldo,
                           mes_filtro=mes_filtro,
                           ano_filtro=ano_filtro)

@app.route('/transacoes', methods=['GET', 'POST'])
def transacoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = request.form['valor']
        categoria = request.form['categoria']
        tipo = request.form['tipo']
        data = request.form['data']
        usuario_id = session['user_id']
        
        conn.execute('''
            INSERT INTO transacoes (descricao, valor, categoria, tipo, data, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (descricao, valor, categoria, tipo, data, usuario_id))
        conn.commit()
        return redirect(url_for('transacoes'))
        
    lista_transacoes = conn.execute('SELECT * FROM transacoes WHERE usuario_id = ? ORDER BY data DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('transacoes.html', transacoes=lista_transacoes)

@app.route('/deletar/<int:id>')
def deletar(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM transacoes WHERE id = ? AND usuario_id = ?', (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('transacoes'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = request.form['valor']
        categoria = request.form['categoria']
        tipo = request.form['tipo']
        data = request.form['data']
        
        conn.execute('''
            UPDATE transacoes 
            SET descricao = ?, valor = ?, categoria = ?, tipo = ?, data = ?
            WHERE id = ? AND usuario_id = ?
        ''', (descricao, valor, categoria, tipo, data, id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('transacoes'))
        
    transacao = conn.execute('SELECT * FROM transacoes WHERE id = ? AND usuario_id = ?', (id, session['user_id'])).fetchone()
    conn.close()
    return render_template('editar.html', transacao=transacao)

@app.route('/exportar')
def exportar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    transacoes = conn.execute('SELECT * FROM transacoes WHERE usuario_id = ? ORDER BY data DESC', (session['user_id'],)).fetchall()
    conn.close()
    
    # Cria o ficheiro CSV na memória
    si = io.StringIO()
    # Usamos o ponto e vírgula para o Excel em português separar as colunas corretamente
    cw = csv.writer(si, delimiter=';') 
    
    # Escreve o cabeçalho
    cw.writerow(['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor (R$)'])
    
    # Escreve as linhas com os dados
    for t in transacoes:
        cw.writerow([t['data'], t['descricao'], t['categoria'], t['tipo'], str(t['valor']).replace('.', ',')])
        
    # Prepara o ficheiro para ser descarregado
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=meu_relatorio_financeiro.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    
    return output

@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user_id = session['user_id']
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        nova_senha = request.form['nova_senha']
        
        # Se o utilizador digitou uma nova senha, atualizamos com criptografia
        if nova_senha.strip():
            senha_criptografada = generate_password_hash(nova_senha)
            conn.execute('''
                UPDATE usuarios SET nome = ?, email = ?, senha = ? WHERE id = ?
            ''', (nome, email, senha_criptografada, user_id))
        else:
            # Se deixou em branco, atualizamos apenas nome e email
            conn.execute('''
                UPDATE usuarios SET nome = ?, email = ? WHERE id = ?
            ''', (nome, email, user_id))
            
        conn.commit()
        flash('Configurações salvas com sucesso!')
        return redirect(url_for('configuracoes'))
        
    # GET: Busca os dados atuais do utilizador para preencher o formulário
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    return render_template('configuracoes.html', usuario=usuario)

if __name__ == '__main__':
    app.run(debug=True)