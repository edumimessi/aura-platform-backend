# AURA Platform — Backend (FastAPI)

API de acompanhamento psiquiátrico ambulatorial.

## Estrutura do Projeto

```
aura-platform-backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuração centralizada
│   ├── database.py            # Conexão com Supabase
│   ├── auth.py                # Validação de JWT
│   ├── models.py              # Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   └── logs.py            # Endpoints de registros diários
│   └── services/
│       ├── __init__.py
│       └── alert_service.py   # Lógica de alertas
├── main.py                    # Aplicação FastAPI
├── requirements.txt           # Dependências Python
├── .env.example              # Exemplo de variáveis de ambiente
├── .gitignore
└── README.md
```

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/edumimessi/aura-platform-backend.git
cd aura-platform-backend
```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` e preencha com suas credenciais:
- `SUPABASE_URL`: URL do seu projeto Supabase
- `SUPABASE_SERVICE_KEY`: Chave de serviço do Supabase
- `SUPABASE_JWT_SECRET`: JWT Secret do Supabase

### 5. Executar a aplicação

```bash
python main.py
```

A API estará disponível em: http://localhost:8000

Documentação interativa (Swagger): http://localhost:8000/docs

## Endpoints

### Registros de Humor

- `POST /api/logs/mood` — Criar registro de humor
- `GET /api/logs/mood/{patient_id}` — Listar registros de humor

### Registros de Crise

- `POST /api/logs/crisis` — Criar registro de crise

## Autenticação

Todos os endpoints requerem um token JWT válido do Supabase no header:

```bash
Authorization: Bearer <supabase_jwt_token>
```

## Segurança

- ✅ Validação de tokens JWT do Supabase
- ✅ Verificação de permissões (médico ou paciente)
- ✅ Validação de dados com Pydantic
- ✅ CORS configurado
- ✅ Variáveis de ambiente protegidas

## Próximos Passos

- [ ] Implementar endpoints de medicações
- [ ] Implementar endpoints de sono
- [ ] Implementar endpoints de exercícios
- [ ] Implementar endpoints de meditação
- [ ] Implementar endpoints de dieta
- [ ] Implementar sistema de alertas completo
- [ ] Implementar dashboard do médico
- [ ] Adicionar testes unitários

## Contribuindo

1. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
2. Commit suas mudanças: `git commit -am 'Adiciona minha feature'`
3. Push para a branch: `git push origin feature/minha-feature`
4. Abra um Pull Request

## Licença

MIT
