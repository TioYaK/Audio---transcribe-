# 🔄 ATUALIZAÇÃO AUTOMÁTICA DE IP - GUIA COMPLETO

## Como Funciona

O sistema atualiza automaticamente o IP público do seu servidor a cada 30 minutos, para que você possa acessar de qualquer lugar sem configurar DDNS.

---

## 🎯 Arquitetura

```
Docker Container (ip-updater)
  ↓ A cada 30 min
Busca IP Público (api.ipify.org)
  ↓
Salva em /app/static/current_ip.txt
  ↓
Cliente Desktop busca esse arquivo
  ↓
Conecta automaticamente!
```

---

## ⚙️ Configuração Inicial

### 1. **Docker (Servidor em Casa)**

O serviço já está configurado! Apenas inicie:

```powershell
docker-compose up -d ip-updater
```

Ou reinicie todo o stack:

```powershell
docker-compose restart
```

### 2. **Cliente Desktop (Trabalho/Outro PC)**

1. Execute `Mirror.ia_Monitor.exe`
2. Na tela de login, clique em **"🔍 Buscar IP Automaticamente"**
3. O IP será atualizado automaticamente!

---

## 🌐 Configurar Port Forwarding (Uma Vez)**

Para acessar de fora da sua rede, configure o roteador:

1. Acesse painel do roteador (geralmente `192.168.1.1`)
2. Vá em **Port Forwarding** ou **Encaminhamento de Porta**
3. Adicione regra:
   - Porta Externa: **8000**
   - Porta Interna: **8000**
   - IP Interno: **192.168.15.2** (seu servidor)
   - Protocolo: **TCP**

---

## 🧪 Como Testar

### Teste 1: Verificar se IP está sendo atualizado

```powershell
# No servidor
docker logs careca-ip-updater --tail 20
```

Deve mostrar algo como:
```
[OK] IP obtido: 200.150.30.45
[OK] IP salvo em /app/static/current_ip.txt
[INFO] Proximo update em 30 minutos...
```

### Teste 2: Acessar arquivo de IP

No navegador:
```
http://192.168.15.2:8000/static/current_ip.txt
```

Deve mostrar seu IP público.

### Teste 3: Endpoint da API

```powershell
curl http://192.168.15.2:8000/api/public-ip
```

Retorna:
```
200.150.30.45
```

---

## 📱 Usando no Cliente

### **Opção 1: Busca Automática (Recomendado)**

1. Abra o cliente desktop
2. Clique em "🔍 Buscar IP Automaticamente"
3. Pronto! Conecta automaticamente

### **Opção 2: Manual**

1. Acesse `http://192.168.15.2:8000/static/current_ip.txt` em casa
2. Copie o IP
3. No cliente, cole: `http://IP_COPIADO:8000`

---

## 🔧 Troubleshooting

### Problema: "IP não encontrado"

**Causa:** Servidor não está acessível ou IP não está sendo atualizado.

**Solução:**
```powershell
# 1. Verificar se serviço está rodando
docker ps | findstr ip-updater

# 2. Ver logs
docker logs careca-ip-updater

# 3. Reiniciar serviço
docker-compose restart ip-updater
```

### Problema: Cliente não conecta mesmo com IP correto

**Causa:** Port Forwarding não configurado ou firewall bloqueando.

**Solução:**
```powershell
# Teste se porta está aberta
Test-NetConnection -ComputerName SEU_IP_PUBLICO -Port 8000
```

### Problema: IP muda muito rápido

**Causa:** Provedor com IP muito dinâmico.

**Solução:** Diminua intervalo de atualização:

No `docker-compose.yml`, linha do `ip-updater`:
```yaml
command: >
  sh -c "while true; do
    python /app/update_ip.py;
    sleep 600;  # 10 minutos (era 1800)
  done"
```

---

## 🚀 Opção Avançada: GitHub Gist (Backup)

Se quiser ter o IP salvo na nuvem (caso servidor fique offline):

### 1. Criar GitHub Token

1. Acesse: https://github.com/settings/tokens
2. "Generate new token" → "Classic"
3. Permissões: `gist`
4. Copie o token

### 2. Configurar no Servidor

No arquivo `.env`:
```env
GITHUB_TOKEN=seu_token_aqui
IP_UPDATE_SIMPLE=false
```

### 3. Reiniciar

```powershell
docker-compose restart ip-updater
```

O Gist será criado automaticamente. Anote o ID que aparece nos logs.

---

## 📊 Monitoramento

Ver último IP atualizado:

```powershell
# Arquivo local
cat static/current_ip.txt

# Via API
curl http://localhost:8000/api/public-ip/json
```

Retorna:
```json
{
  "ip": "200.150.30.45",
  "updated_at": "2025-12-21T23:30:00Z",
  "server": "Mirror.ia"
}
```

---

## ✅ Checklist de Configuração

- [ ] Docker rodando com `ip-updater`
- [ ] Arquivo `/app/static/current_ip.txt` sendo criado
- [ ] Port Forwarding configurado no roteador (porta 8000)
- [ ] Cliente desktop consegue buscar IP automaticamente
- [ ] Conexão funcionando de fora da rede local

---

## 💡 Dicas

1. **Salve IP na rede local:** Use `192.168.15.2:8000` quando estiver em casa
2. **Auto-discover:** Sempre use o botão de busca automática no trabalho
3. **Backup:** Anote seu IP público manualmente também
4. **Firewall:** Alguns firewalls corporativos podem bloquear

---

## 🎯 Comparação

| Método | Configuração | Confiabilidade | Custo |
|--------|--------------|----------------|-------|
| **Auto IP Update** | Fácil | Alta | Grátis |
| **DDNS (DuckDNS)** | Média | Muito Alta | Grátis |
| **IP Fixo ISP** | Nenhuma | Máxima | Pago |
| **VPN (Tailscale)** | Fácil | Máxima | Grátis |

**Recomendação:**
- **Para uso pessoal:** Auto IP Update (esta solução)
- **Para produção:** VPN (Tailscale) ou DDNS
- **Para empresa:** IP Fixo + VPN

---

Feito! Agora você pode acessar seu servidor de qualquer lugar automaticamente! 🚀
