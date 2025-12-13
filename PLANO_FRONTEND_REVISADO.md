# PLANO DE MELHORIAS FRONTEND - Versão Conservadora

## Situação Atual
- Backend totalmente refatorado ✅ (Tiers 1, 2 e 3)
- Frontend ainda usando `script.js` monolítico (funcional)

## Estratégia Revisada

### Opção 1: Manter Frontend Atual + Adicionar Features
**Prós:**
- Não quebra nada
- Adiciona funcionalidades gradualmente
- Usuário pode usar o sistema enquanto melhoramos

**Contras:**
- Código continua grande
- Dificulta manutenção futura

### Opção 2: Refatoração Completa (Tentativa Anterior - FALHOU)
**Problema identificado:**
- ES6 modules não carregaram corretamente
- Possível problema de CORS ou MIME types
- Falta de fallback adequado

### Opção 3: Refatoração Híbrida (RECOMENDADA)
**Abordagem:**
1. Manter `script.js` principal
2. Extrair apenas funções grandes para arquivos separados
3. Carregar via `<script src="">` tradicional (não modules)
4. Testar cada extração individualmente

## Próximos Passos Sugeridos

**Imediato (Tier 3 - Funcionalidade):**
- Adicionar interface de Regras Dinâmicas no painel Admin existente
- Endpoint já existe no backend (`/api/admin/rules`)
- Apenas adicionar HTML/JS no admin panel

**Futuro (Refatoração Segura):**
- Extrair player de áudio para `player.js`
- Extrair admin para `admin.js`
- Usar scripts tradicionais, não ES6 modules

Qual abordagem você prefere?
