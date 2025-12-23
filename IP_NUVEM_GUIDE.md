# ☁️ MIRROR.IA - ACESSO REMOTO COM IP NA NUVEM

## 🎯 Como Funciona

Seu IP público é **automaticamente salvo em um serviço na nuvem** (Dpaste.com) a cada 30 minutos.  
O cliente desktop **busca automaticamente** esse IP de qualquer lugar do mundo!

```
Docker (Casa) → Atualiza IP a cada 30 min → Dpaste.com (Nuvem Pública)
                                              ↓
Cliente Desktop (Trabalho) → Busca IP → Conecta Automaticamente!
```

---

## ✅ **ZERO CONFIGURAÇÃO NECESSÁRIA!**

Não precisa:
- ❌ DNS Dinâmico (DuckDNS, No-IP)
- ❌ Conta no Google
- ❌ Tokens ou autenticação
- ❌ Configurar nada manualmente

---

## 🚀 Como Usar

### **1. No Servidor (Casa) - Configuração Automática**

O Docker já está configurado para att atualizar o IP. Basta rodar:

```powershell
# Rebuild e restart
docker-compose up -d --build
```

O serviço `ip-updater` vai:
1. Obter seu IP público atual
2. Salvar em **Dpaste.com** (público, sem login)
3. Atualizar a cada **30 minutos**

---

### **2. No Cliente Desktop (Qualquer Lugar)**

1. Execute **`Mirror.ia_Monitor.exe`**
2. **AUTOMÁTICO:** Ao abrir, busca o IP da nuvem
3. Se não encontrar, clique **"🔍 Buscar IP Automaticamente"**
4. Pronto! Conecta automaticamente

---

## 📊 Como Verificar se Está Funcionando

### **Teste 1: Ver logs do atualizador**

```powershell
docker logs careca-ip-updater --tail 20
```

Deve mostrar:
```
[OK] IP obtido: 177.45.125.118
[OK] Dpaste atualizado: https://dpaste.com/XXXXX
[OK] URL Raw: https://dpaste.com/XXXXX.txt
[INFO] Proximo update em 30 minutos...
```

### **Teste 2: Acessar URL pública**

```powershell
# Ver qual é a URL
cat static/paste_raw_url.txt
```

Acesse essa URL no navegador de qualquer lugar:
```
https://dpaste.com/XXXXX.txt
```

Deve mostrar:
```json
{
  "ip": "177.45.125.118",
  "updated_at": "2025-12-22T01:37:07",
  "server": "Mirror.ia"
}
```

---

## 🌐 Serviços Usados (Automático)

| Serviço | Prioridade | Requer Auth? | Duração |
|---------|-----------|--------------|---------|
| **Dpaste.com** | 1º | ❌ Não | 1 ano |
| **Mozilla Paste** | 2º (fallback) | ❌ Não | 1 ano |
| **GitHub Gist** | 3º (opcional) | ✅ Sim (token) | Permanente |

---

## ⚙️ Lógica de Busca do Cliente

O cliente tenta na seguinte ordem:

1. **Servidor salvo anteriormente** → Pega IP atualizado via API
2. **Servidor local (LAN)** → `192.168.15.2:8000`
3. **Dpaste na Nuvem** → Busca URL salva + pega IP
4. **Manual** → Você digita

---

## 🔧 Configuração Avançada (Opcional)

### **Usar GitHub Gist (mais confiável)**

1. Criar token: https://github.com/settings/tokens
   - Permissões: `gist`

2. Adicionar no `.env`:
   ```env
   GITHUB_TOKEN=seu_token_aqui
   ```

3. Reiniciar:
   ```powershell
   docker-compose restart ip-updater
   ```

O Gist será criado automaticamente e a URL aparecerá nos logs.

---

## 📱  Cenários de Uso

### **Cenário 1: Trabalho (Fora da Rede)**
1. Abre o cliente desktop
2. Automático: Busca IP do Dpaste
3. Conecta em `http://177.45.125.118:8000`

### **Cenário 2: Em Casa (Mesma Rede)**
1. Abre o cliente
2. Usa `http://192.168.15.2:8000` (mais rápido)
3. Ou deixa buscar automaticamente

### **Cenário 3: IP Mudou**
1. Docker atualiza automaticamente a cada 30 min
2. Cliente busca o novo IP na próxima abertura
3. Ou clica em "Buscar IP Automaticamente"

---

## 🛠 Troubleshooting

### Problema: "IP não encontrado"

**Causa:** Dpaste não foi atualizado ou está inacessível.

**Solução:**
```powershell
# 1. Testar manualmente
python update_ip.py

# 2. Ver se gerou URL
cat static/paste_raw_url.txt

# 3. Testar acesso
curl https://dpaste.com/XXXXX.txt
```

### Problema: Cliente não conecta

**Verificar:**
```powershell
# IP atual
curl https://api.ipify.org

# Port forwarding OK?
Test-NetConnection -ComputerName SEU_IP -Port 8000
```

### Problema: Docker não está atualizando

```powershell
# Ver se serviço está rodando
docker ps | findstr ip-updater

# Forçar update manual
docker exec careca-ip-updater python /app/update_ip.py
```

---

## 📈 Monitoramento

### Ver histórico de atualizações:

```powershell
# Logs recentes
docker logs careca-ip-updater --tail 50

# Acompanhar em tempo real
docker logs -f careca-ip-updater
```

### Forçar atualização imediata:

```powershell
docker restart careca-ip-updater
```

---

## 🔒 Segurança

**É seguro?**
- ✅ Dpaste é público mas **ReadOnly** (ninguém pode editar)
- ✅ Apenas seu IP é exposto (já está público de qualquer forma)
- ✅ Nenhuma credencial ou dados sensíveis
- ✅ HTTPS em todas as comunicações

**Melhorar segurança:**
1. Use **VPN (Tailscale)** para acesso criptografado
2. Configure **autenticação forte** no app
3. Use **Firewall** para limitar IPs permitidos

---

## 🎯 Comparação com Alternativas

| Método | Setup | Confiabilidade | Custo | Segurança |
|--------|-------|----------------|-------|-----------|
| **IP na Nuvem (Esta solução)** | Automático | Alta | Grátis | Média |
| **DDNS (DuckDNS)** | 5 min | Muito Alta | Grátis | Média |
| **IP Fixo ISP** | Ligar pro provedor | Máxima | R$ 30-100/mês | Alta |
| **VPN (Tailscale)** | 10 min | Máxima | Grátis | Máxima |

---

## ✅ Checklist Pós-Instalação

- [ ] Docker rodando com `ip-updater`
- [ ] Logs mostram "Dpaste atualizado"
- [ ] Arquivo `static/paste_raw_url.txt` existe
- [ ] URL do Dpaste acessível externamente
- [ ] Port forwarding configurado (porta 8000)
- [ ] Cliente desktop consegue buscar IP automaticamente

---

## 🚀 **Resultado Final**

**Antes:**
- Tinha que anotar IP manualmente
- IP mudava e perdia acesso
- Precisava configurar DNS dinâmico

**Agora:**
- ✅ IP atualiza automaticamente na nuvem
- ✅ Cliente busca sozinho de qualquer lugar
- ✅ Zero configuração manual
- ✅ Funciona de qualquer rede

---

**Seu IP está sempre acessível em:** https://dpaste.com/XXXXX.txt

**Basta abrir o cliente e ele conecta automaticamente!** 🎉
