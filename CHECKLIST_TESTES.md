# ✅ Checklist de Testes - Sistema de Transcrição

## 🎯 Objetivo
Verificar se todas as correções foram aplicadas corretamente e o sistema está funcionando como esperado.

---

## 📋 Pré-requisitos
- [ ] Docker está rodando
- [ ] Container `audio---transcribe--transcription-service-1` está ativo
- [ ] Navegador com console aberto (F12)
- [ ] Acesso ao sistema em http://localhost:8000

---

## 🔐 Teste 1: Login e Autenticação

### Admin Login
- [ ] Acesse http://localhost:8000/login
- [ ] Login com username: `admin` e senha vazia (ou qualquer senha)
- [ ] Deve redirecionar para o Dashboard
- [ ] Menu lateral deve mostrar opções: Dashboard, Relatórios, Juntar (QLD), Admin, Terminal, Exportar

### Verificação de Permissões
- [ ] Link "Admin" está visível no menu lateral
- [ ] Link "Terminal" está visível no menu lateral
- [ ] Ambos devem estar visíveis apenas para admin

---

## 🧹 Teste 2: Botão "Limpar Histórico" (Dashboard)

### Preparação
- [ ] Certifique-se de que há pelo menos 1 transcrição no histórico
- [ ] Se não houver, faça upload de um arquivo de áudio

### Execução
- [ ] Abra o Console do navegador (F12)
- [ ] Clique no botão de lixeira (🗑️) ao lado do título "Histórico"
- [ ] Confirme a ação no diálogo

### Verificações
- [ ] ✅ Toast verde aparece com mensagem "Histórico limpo!"
- [ ] ✅ Tabela de histórico fica vazia
- [ ] ✅ Contador de uso (canto superior direito) é atualizado
- [ ] ✅ Console mostra: `Clear response: {deleted: X}` (onde X é o número de itens)
- [ ] ✅ Não há erros em vermelho no console

### Logs Esperados no Console
```
Clear response: {deleted: 5}
Histórico limpo!
DEBUG: loadHistory starting... [timestamp]
DEBUG: Data received from API: 0
```

---

## 🔧 Teste 3: Botão "Limpar Banco/Cache" (Terminal - Admin)

### Preparação
- [ ] Faça upload de pelo menos 2 arquivos de áudio
- [ ] Aguarde a conclusão das transcrições

### Execução
- [ ] Clique em "Terminal" no menu lateral
- [ ] Verifique que a view do Terminal está visível
- [ ] Abra o Console do navegador (F12)
- [ ] Clique no botão "Limpar Banco/Cache" no topo da página
- [ ] Confirme a ação no diálogo de confirmação

### Verificações
- [ ] ✅ Toast verde aparece com mensagem "Banco de dados limpo!"
- [ ] ✅ Volte ao Dashboard e verifique que o histórico está vazio
- [ ] ✅ Contador de uso mostra "0 / ∞" (para admin)
- [ ] ✅ Console mostra: `Clear response: {deleted: X}`
- [ ] ✅ Não há erros em vermelho no console

### Logs Esperados no Console
```
adminClearCache called
Sending clean request...
Clear response: {deleted: 10}
Banco de dados limpo!
DEBUG: loadHistory starting... [timestamp]
```

---

## 🔒 Teste 4: Verificações de Autorização (Admin)

### Teste 4.1: Acesso a Transcrições de Outros Usuários
- [ ] Crie um usuário normal (se ainda não existir)
- [ ] Faça upload de arquivo como usuário normal
- [ ] Faça logout e login como admin
- [ ] Clique em "Ver Todos" no Dashboard
- [ ] Tente visualizar a transcrição do outro usuário

**Resultado esperado:**
- [ ] ✅ Admin consegue visualizar transcrições de outros usuários
- [ ] ✅ Não aparece erro 403 (Não autorizado)

### Teste 4.2: Download de Áudio de Outros Usuários
- [ ] Com transcrição de outro usuário visível
- [ ] Clique no botão de download de áudio

**Resultado esperado:**
- [ ] ✅ Download inicia sem erros
- [ ] ✅ Não aparece erro 403

### Teste 4.3: Renomear Tarefa de Outro Usuário
- [ ] Com transcrição de outro usuário visível
- [ ] Clique no botão de renomear (lápis)
- [ ] Digite novo nome e salve

**Resultado esperado:**
- [ ] ✅ Nome é alterado com sucesso
- [ ] ✅ Não aparece erro 403

---

## 🚨 Teste 5: Tratamento de Erros

### Teste 5.1: Servidor Offline
- [ ] Pare o container: `docker-compose down`
- [ ] Tente clicar em "Limpar Histórico"

**Resultado esperado:**
- [ ] ✅ Aparece alert com mensagem de erro
- [ ] ✅ Console mostra erro detalhado
- [ ] ✅ Interface não trava

### Teste 5.2: Reiniciar Servidor
- [ ] Inicie o container: `docker-compose up -d`
- [ ] Aguarde ~10 segundos
- [ ] Recarregue a página
- [ ] Faça login novamente

**Resultado esperado:**
- [ ] ✅ Sistema volta a funcionar normalmente

---

## 📊 Teste 6: Funcionalidades Gerais

### Upload e Transcrição
- [ ] Faça upload de um arquivo de áudio
- [ ] Verifique que aparece na seção "Em Processamento"
- [ ] Aguarde conclusão
- [ ] Verifique que aparece no histórico

### Visualização de Transcrição
- [ ] Clique no botão "Ver" (olho) de uma transcrição
- [ ] Verifique que o modal abre
- [ ] Verifique que o texto da transcrição está visível
- [ ] Verifique que o player de áudio funciona

### Relatórios
- [ ] Clique em "Relatórios" no menu lateral
- [ ] Verifique que as estatísticas são exibidas
- [ ] Verifique que o gráfico é renderizado

### Exportar
- [ ] Clique em "Exportar" no menu lateral
- [ ] Verifique que o download do arquivo .txt inicia
- [ ] Abra o arquivo e verifique o conteúdo

---

## 🎨 Teste 7: Interface do Usuário

### Tema Escuro/Claro
- [ ] Clique no botão de tema no rodapé do menu lateral
- [ ] Verifique que o tema alterna corretamente
- [ ] Verifique que a preferência é salva (recarregue a página)

### Responsividade
- [ ] Redimensione a janela do navegador
- [ ] Verifique que a interface se adapta
- [ ] Teste em diferentes tamanhos de tela

---

## 📝 Checklist Final

### Funcionalidades Críticas
- [ ] ✅ Login funciona
- [ ] ✅ Upload funciona
- [ ] ✅ Transcrição funciona
- [ ] ✅ Visualização funciona
- [ ] ✅ Download funciona
- [ ] ✅ Botão "Limpar Histórico" funciona
- [ ] ✅ Botão "Limpar Banco/Cache" funciona
- [ ] ✅ Verificações de admin funcionam
- [ ] ✅ Relatórios funcionam
- [ ] ✅ Exportar funciona

### Qualidade
- [ ] ✅ Sem erros no console
- [ ] ✅ Toasts aparecem corretamente
- [ ] ✅ Feedback visual adequado
- [ ] ✅ Tratamento de erros funciona
- [ ] ✅ Interface responsiva

---

## 🐛 Problemas Encontrados

Se você encontrar algum problema durante os testes, anote aqui:

### Problema 1
**Descrição:**
**Passos para reproduzir:**
**Erro no console:**
**Severidade:** [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo

### Problema 2
**Descrição:**
**Passos para reproduzir:**
**Erro no console:**
**Severidade:** [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo

---

## ✅ Conclusão

**Data do teste:** ___/___/_____
**Testado por:** _________________
**Resultado geral:** [ ] ✅ Aprovado [ ] ❌ Reprovado [ ] ⚠️ Com ressalvas

**Observações:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

**Nota:** Este checklist deve ser executado após cada deploy ou atualização significativa do sistema.
