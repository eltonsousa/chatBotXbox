## **Chatbot de Atendimento para Conserto e Desbloqueio de Xbox 360**

Este é um chatbot para WhatsApp desenvolvido em Python, utilizando o framework Flask e o banco de dados SQLite. O bot foi projetado para automatizar o atendimento a clientes interessados em serviços de conserto, desbloqueio e cópia de jogos para consoles Xbox 360\. Ele coleta informações como nome, e-mail e dados do console para gerar um resumo do pedido.

---

### **Funcionalidades**

* **Conversa em Fluxo:** O bot guia o usuário passo a passo, solicitando informações em uma sequência lógica.  
* **Coleta de Dados:** Registra nome, e-mail, modelo e ano do console, tipo de armazenamento e jogos selecionados.  
* **Armazenamento de Dados:** Salva todas as informações em um banco de dados local (`chatbot.db`).  
* **Encerramento da Conversa:** O usuário pode encerrar a conversa a qualquer momento com comandos como `encerrar`, `parar`, `cancelar` ou `sair`.  
* **Resposta Dinâmica:** A mensagem de saudação inclui o nome do usuário após ele se apresentar.

---

### **Pré-requisitos**

Antes de começar, certifique-se de que você tem o seguinte instalado:

* **Python 3.x:** (Recomendado versão 3.8+)  
* **pip:** Gerenciador de pacotes do Python.  
* **git:** Para clonar o repositório.  
* **ngrok:** Para expor o seu servidor local para a internet.

---

### **Passo a Passo para Configuração e Execução**

#### **Passo 1: Clone o Repositório**

Abra seu terminal e clone o projeto para sua máquina:

Bash  
git clone \[link do seu repositorio\]  
cd \[nome da pasta do projeto\]

#### **Passo 2: Configure o Ambiente Virtual**

É altamente recomendado usar um ambiente virtual para gerenciar as dependências do projeto. Isso evita conflitos com outras bibliotecas instaladas no seu computador.

Crie um arquivo chamado **`requirements.txt`** na raiz do projeto e adicione o seguinte conteúdo:  
Flask  
twilio  
python-dotenv  
requests

1. 

Crie o ambiente virtual:  
Bash  
python \-m venv venv

2.   
3. **Ative o ambiente virtual.** Este é um passo crucial:

**No Windows:**  
Bash  
venv\\Scripts\\activate

* 

**No Mac/Linux:**  
Bash  
source venv/bin/activate

*   
4. Você saberá que deu certo quando a palavra `(venv)` aparecer no início da linha do seu terminal.

Instale todas as dependências do projeto de uma só vez:  
Bash  
pip install \-r requirements.txt

5. 

#### **Passo 3: Configure as Credenciais da API**

Por segurança, as credenciais da sua conta Meta (WhatsApp Cloud API) ou Twilio não devem estar no código.

1. Crie um arquivo chamado **`twilio_env`** na raiz do seu projeto.

Dentro desse arquivo, adicione suas credenciais no formato `KEY=VALUE`, substituindo os valores pelos seus tokens e IDs reais:  
META\_TOKEN=sua\_chave\_de\_acesso\_aqui  
PHONE\_NUMBER\_ID=seu\_id\_de\_telefone\_aqui  
VERIFY\_TOKEN=seu\_token\_de\_verificacao\_aqui

2. 

#### **Passo 4: Inicie o Chatbot**

Com tudo configurado, você pode iniciar o seu bot. Lembre-se de manter o ambiente virtual ativado (`(venv)`).

**Inicie o servidor Flask:**  
Bash  
python app.py

1. O servidor será executado na porta `5000`.

**Abra um novo terminal** e inicie o ngrok para criar um túnel público para a porta `5000`:  
Bash  
ngrok http 5000

2. O ngrok irá fornecer um **URL público**. Copie-o.  
3. **Configure o Webhook:** No painel de configurações da sua conta Twilio ou Meta, cole o URL que o ngrok te forneceu, adicionando o endpoint `/whatsapp_webhook` no final. **Exemplo:** `https://[URL_DO_NGROK].ngrok-free.app/whatsapp_webhook`

---

### **Como Usar o Bot**

Após configurar o webhook, o bot está pronto para ser usado. Basta enviar uma mensagem para o número do seu WhatsApp vinculado.

* Para iniciar, envie `olá`, `oi` ou `iniciar`.  
* Para encerrar a conversa a qualquer momento, envie `encerrar`, `parar`, `cancelar` ou `sair`.

---

### **Estrutura do Projeto**

* `app.py`: O código principal do chatbot.  
* `chatbot.db`: O banco de dados SQLite que armazena os leads.  
* `requirements.txt`: Lista de dependências do projeto.  
* `twilio_env`: Arquivo para variáveis de ambiente (credenciais).  
* `venv/`: Pasta do ambiente virtual.

---

### **Construído com:**

* **Flask:** Framework web para Python.  
* **Twilio / WhatsApp Cloud API (Meta):** Serviço para envio e recebimento de mensagens.  
* **SQLite:** Banco de dados leve e integrado.  
* **ngrok:** Túnel para expor o servidor local.  
* **python-dotenv:** Biblioteca para gerenciar variáveis de ambiente.

