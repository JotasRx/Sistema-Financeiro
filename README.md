# Sistema Web de Controle Financeiro Pessoal

Este projeto consiste em uma plataforma web desenvolvida como Trabalho de Conclusão de Curso (TCC) para o curso de Sistemas de Informação. O objetivo é auxiliar usuários na organização, planejamento e gestão de suas finanças diárias, permitindo o registro de receitas e despesas e a visualização de indicadores financeiros.

## 🚀 Tecnologias Utilizadas
O projeto foi desenvolvido utilizando as seguintes tecnologias:
- **Backend:** Python com Flask
- **Banco de Dados:** MySQL
- **Frontend:** HTML5, CSS3, JavaScript e Chart.js (para gráficos)

## 📋 Pré-requisitos
Para executar este projeto em sua máquina, você precisará de:
1. Python instalado (versão 3.x).
2. Servidor MySQL instalado e rodando (Ex: XAMPP, MySQL Server).
3. Gerenciador de pacotes `pip`.

## ⚙️ Como configurar e rodar
1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/JotaPe-art/Sistema-web-Financeiro](https://github.com/JotaPe-art/Sistema-web-Financeiro)
Instale as dependências:

Bash
pip install flask mysql-connector-python python-dotenv
Configuração do Banco:

Crie um banco de dados no MySQL chamado sistema_financeiro.

Na raiz do projeto, crie um arquivo chamado .env e adicione suas credenciais:

Plaintext
FLASK_SECRET_KEY=sua_chave_secreta
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=sistema_financeiro
Execução:

Rode o arquivo de inicialização das tabelas:

Bash
python setup_mysql.py
Inicie a aplicação:

Bash
python app.py
Acesse no navegador: http://127.0.0.1:5000

👤 Autor
João Pedro Carvalho
Projeto desenvolvido para o curso de Sistemas de Informação - Universidade de Mogi das Cruzes (2026).