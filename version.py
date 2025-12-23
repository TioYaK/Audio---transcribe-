# Mirror.ia - Auto Updater
# Arquivo de versão e changelog

VERSION = "1.0.36"
BUILD_DATE = "2025-12-22"

CHANGELOG = """
# Changelog

## v1.0.36 (2025-12-22)
- VISUAL: Limpeza automática do nome na visualização de detalhes
- Remove automaticamente extensão (.wav, .mp3) e parenteses (ex: '(1)') do título
- Mantém o nome do arquivo original no backend, apenas visualização é alterada
- Melhoria na legibilidade de títulos longos



## v1.0.31 (2025-12-22)
- FIX CRÍTICO LOGIN: Reescrita lógica de ativação do botão "Entrar"
- Garante que a ação de login seja vinculada corretamente após verificação de conexão

## v1.0.30 (2025-12-22)
- FIX LOGIN: Corrigido loop infinito "Aguarde..." ao alternar abas
- ADMIN: Adicionado botão "Promover/Revogar Admin" na gestão de usuários

## v1.0.29 (2025-12-22)
- FIX CRÍTICO UI CODE: Corrigido erro "RoundedButton object has no attribute text"
- Todos os botões do sistema agora funcionam perfeitamente

## v1.0.28 (2025-12-22)
- FIX CRÍTICO BOTÕES: Mecanismo de clique totalmente reescrito
- Adicionado suporte a clique nos elementos internos (texto/borda) para garantir execução

## v1.0.27 (2025-12-22)
- FIX UI: "Mirror.ia Server" agora aparece centralizado
- FIX BOTÃO: Botão "Entrar" recupera funcionalidade após falha de conexão

## v1.0.26 (2025-12-22)
- TESTE DE REDUNDÂNCIA: Validando a estabilidade do novo motor de updates
- Esta versão garante que o ciclo de atualizações está totalmente corrigido

## v1.0.25 (2025-12-22)
- FIX RESTART: Método de reinício alterado para usar Explorer
- Resolve em definitivo o erro de DLL ao reiniciar automaticamente

## v1.0.24 (2025-12-22)
- FIX UI: Correção crítica no botão de Login que ficava preso em "Verificando"
- O botão agora atualiza corretamente o texto para "Entrar"

## v1.0.23 (2025-12-22)
- FIX FINAL INSTALAÇÃO: Aumentado delay de restart para 10s
- Resolve erro de DLL em máquinas lentas

## v1.0.22 (2025-12-22)
- FIX CRÍTICO INSTALAÇÃO: Aumentado tempo de espera no script de atualização
- Garantia de flush de disco ao baixar atualização

## v1.0.21 (2025-12-22)
- FIX CRÍTICO: Resolve permanentemente erro de conexão na porta 80
- O servidor agora fornece URL absoluta para garantir download na porta 8000

## v1.0.20 (2025-12-22)
- TESTE AUTO-UPDATER: Validando nova tentativa de atualização
- Melhoria interna de logging

## v1.0.19 (2025-12-22)
- FIX CRÍTICO: Resolve erro de conexão (Conexão Recusada)
- O atualizador agora usa corretamente a porta 8000

## v1.0.18 (2025-12-22)
- SUCESSO! Auto-Update validado.
- Se você está lendo isso, o sistema de atualização automática funcionou perfeitamente.
- Adeus erros de DLL e URL inválida! 🚀

## v1.0.17 (2025-12-22)
- FIX CRÍTICO: Resolve erro "Invalid URL" ao tentar atualizar
- Sistema de Auto-Update agora totalmente robusto e silencioso
- Todas as correções de UI e Login aplicadas

## v1.0.16 (2025-12-22)
- FIX: Texto do botão de login corrigido ("Entrar")
- UI Cleaner: Botão de novidades removido
- Clique no número da versão para ver changelog
- Melhoria na responsividade do botão

## v1.0.15 (2025-12-22)
- NOVO: Atualizações automáticas silenciosas (sem popup)
- FIX: Botão de Login libera corretamente após busca de IP
- FIX: Busca de IP inicia automaticamente ao abrir o app
- Validação MD5 para garantir download seguro

## v1.0.14 (2025-12-22)
- SEGURANÇA MÁXIMA: Validação de Assinatura MD5 nas atualizações
- Impede instalação se o download estiver corrompido (Erro Python DLL)
- Script de publicação atualizado para gerar assinaturas

## v1.0.13 (2025-12-22)
- Melhorias internas de estabilidade
- Versão de validação do Auto-Updater

## v1.0.12 (2025-12-22)
- FIX: Correção crítica na exibição dos campos de login
- UI agora renderiza corretamente após verificação de conexão
- Melhorias na estabilidade do fluxo de inicialização

## v1.0.11 (2025-12-22)
- FIX CRÍTICO: Novo sistema de atualização "Rename & Swap"
- Resolve erro de "Python DLL" ao atualizar
- Atualização muito mais segura e confiável

## v1.0.10 (2025-12-22)
- NOVO: Botão de Login inteligente ("Aguarde..." -> "Entrar")
- SEGURANÇA: Botão só libera após confirmação de conexão com servidor
- OTIMIZAÇÃO: Verificação de status do servidor em tempo real

## v1.0.9 (2025-12-22)
- FIX: Robustez do sistema de auto-update
- Novo sistema de verificação de integridade de download
- Aumento do tempo de espera para substituição de arquivos

## v1.0.8 (2025-12-22)
- NOVO: Exibição da versão no rodapé (canto inferior direito)
- Melhorias visuais na tela de login/registro

## v1.0.7 (2025-12-22)
- OTIMIZAÇÃO: Campo IP servidor removido do registro
- OTIMIZAÇÃO: Registro usa configuração do Login
- CORRIGIDO: Mais ajustes de espaçamento

## v1.0.6 (2025-12-22)
- Ajustes de layout para telas menores
- Redução de espaçamentos para evitar cortes
- Botão CRIAR CONTA agora sempre visível
- Logo ajustado no topo

## v1.0.5 (2025-12-22)
- CORRIGIDO: Toggle LOGIN/CRIAR CONTA agora funciona
- CORRIGIDO: Logo não cortado (janela maior)
- NOVO: Botao Ver Novidades para mostrar changelog
- MELHORIA: Mirror.ia Server aparece centralizado
- MELHORIA: Janela redimensionavel com tamanho minimo

## v1.0.3 (2025-12-21)
- Correcao: Removido usuario admin duplicado
- Confirmado: Novos usuarios sao criados como membros
- Melhorias gerais de estabilidade

## v1.0.2 (2025-12-21)
- Correcao: Botao Criar Conta agora visivel
- Melhoria: Nome amigavel 'Mirror.ia Server' ao inves de IP
- Protecao do usuario admin em todas as interfaces
- Auto-updater funcionando

## v1.0.0 (2025-12-21)
- Sistema de auto-discovery de IP via Dpaste
- Botao de registro de novos usuarios  
- Protecao do usuario admin contra exclusao
- Auto-updater implementado
- Busca automatica de IP ao iniciar
- Suporte a tela de cadastro completa
"""
