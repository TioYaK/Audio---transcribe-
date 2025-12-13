# Análise Sistêmica e Proposta de Evolução - Careca.io (Fase 2.0)

## 1. Diagnóstico do Sistema Atual

Após revisão detalhada do código fonte, infraestrutura (Docker) e banco de dados, apresento o diagnóstico do estado atual da aplicação.

### 🏗️ Arquitetura e Backend
*   **Ponto Forte:** O uso de **FastAPI** com `faster-whisper` é uma excelente escolha para performance. A arquitetura de microsserviços via Docker está bem encaminhada.
*   **Ponto Crítico (Fila de Tarefas):** O sistema utiliza uma fila em memória (`asyncio.Queue`) com um consumidor simples (`app.core.worker`).
    *   *Risco:* Se o contêiner reiniciar, **todas as tarefas na fila são perdidas**. A "recuperação" no startup tenta consertar, mas perde as `options` (configurações) originais do usuário.
*   **Banco de Dados:** O uso de **SQLite** (`transcriptions.db`) é adequado para MVP, mas inadequado para produção com concorrência (múltiplos workers) e não suporta bem operações de escrita simultânea.
*   **Modularidade:** A classe `WhisperService` tornou-se um "God Object" (faz tudo: transcreve, melhora áudio, dinstingue falantes, analisa negócio). A lógica de negócio ("Economia Programada") está hardcoded no core.

### 🎨 Frontend e UX
*   **Estética:** O design visual é moderno (Glassmorphism, Phosphor Icons), o que é excelente.
*   **Código:** O arquivo `static/script.js` possui mais de 2.000 linhas.
    *   *Problema:* Dificulta manutenção, debug e criação de novas features. Mistura lógica de auth, player de áudio, admin e websocket/polling.
*   **Player de Áudio:** A implementação do WaveSurfer é funcional mas complexa.

### 🧠 Inteligência Artificial
*   **Diarização:** Está rodando em CPU para economizar VRAM.
    *   *Gargalo:* Isso torna o processo lento para áudios longos.
*   **Análise de Negócio:** Atualmente "hardcoded" para o caso de uso "Bradesco". Se quiser analisar outro produto, precisa alterar o código Python.

### 🔒 Segurança
*   **Log de Senha:** O sistema gera e loga a senha de admin no console se não estiver definida. Em um ambiente de produção real com logs centralizados, isso é uma falha de segurança.
*   **Gestão de Sessão:** Baseada em tokens simples, sem refresh tokens robustos visíveis na análise inicial.

---

## 2. Proposta de Evolução (Roadmap)

Sugiro dividir as melhorias em 3 tiers baseados na complexidade e impacto.

### 🚀 Tier 1: Estabilização e Core (Imediato)
*Foco: Resolver débitos técnicos críticos e garantir que o sistema não perca dados.*

1.  **Refatoração do Backend (Prioridade Alta):**
    *   Quebrar `WhisperService` em 3 serviços especializados:
        *   `TranscriberService`: Foca apenas em áudio -> texto.
        *   `DiarizationService`: Isolado (permitindo escalar separadamente).
        *   `AnalysisService`: Serviço agnóstico que recebe texto e aplica regras.
2.  **Módulos JS no Frontend:**
    *   Dividir `script.js` em módulos ES6: `auth.js`, `player.js`, `dashboard.js`, `admin.js`. Isso facilitará muito a manutenção futura.
3.  **Correção de Segurança:**
    *   Remover log de senha em texto plano.
4.  **Persistência de Fila (Robustez):**
    *   Mesmo sem Redis agora, salvar o "estado da fila" no banco de dados ANTES de processar, garantindo que as `options` (timestamps, diarização) não se percam num crash.

### ⚡ Tier 2: Infraestrutura Professional (Recomendado)
*Foco: Performance e Escalabilidade.*

1.  **Migração para PostgreSQL:**
    *   Substituir SQLite por PostgreSQL no Docker. Melhora drástica na confiabilidade e permite múltiplos workers sem travar o banco.
2.  **Fila com Redis + Celery/Arq:**
    *   Substituir `asyncio.Queue` por Redis. Isso garante que tarefas sobrevivam a reboots e permite visualizar filas em tempo real de forma profissional.
3.  **Diarização em GPU (Opcional):**
    *   Habilitar flag para rodar SpeechBrain na GPU se houver VRAM disponível (>6GB), reduzindo tempo de processamento de minutos para segundos.

### 💎 Tier 3: Features Premium & Flexibilidade
*Foco: Agregar valor ao produto final.*

1.  **Criador de Análises Dinâmico (No-Code):**
    *   Criar uma interface onde o Admin define "Palavras-chave", "Termos Proibidos" e "Tópicos" via painel, salvando no banco.
    *   *Benefício:* O sistema serve para qualquer cliente (não só Bradesco) sem mudar uma linha de código.
2.  **Editor de Transcrição Interativo:**
    *   Permitir que o usuário clique numa palavra na transcrição e a corrija, atualizando o banco e re-gerando a análise.
3.  **Player "Word-Level":**
    *   Ao clicar na palavra no texto, o áudio pula EXATAMENTE para aquele milissegundo (já suportado pelo backend, falta refino no frontend).

---

## 3. Plano de Ação Sugerido (Próximos Passos)

Minha recomendação é começarmos pelo **Tier 1 (Refatoração e Estabilização)** para limpar a base de código antes de adicionar complexidade.

**Deseja que eu inicie por qual frente?**
1.  **Organização do Frontend:** Modularizar o `script.js` (Impacto visual imediato na organização).
2.  **Refatoração do Backend:** Dividir o `WhisperService` e proteger a fila de tarefas.
3.  **Infraestrutura:** Configurar o PostgreSQL e preparar o terreno para Redis.

Aguardo sua instrução!
