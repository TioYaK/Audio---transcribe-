# 📦 Mirror.ia - GUIA DE ACESSO REMOTO

## Como usar em computadores remotos (Trabalho, etc)

### ✅ Opção 1: Executável Portátil (.exe) - **RECOMENDADO**

#### **Passo 1: Criar o executável (Fazer uma vez na sua máquina)**

```powershell
# No diretório do projeto
python build_portable.py
```

Isso vai gerar: `dist/Mirror.ia_Monitor.exe` (~50-80 MB)

#### **Passo 2: Copiar para o outro computador**

- Copie `Mirror.ia_Monitor.exe` para um pendrive ou envie por email
- Cole no computador de destino (pode ser qualquer pasta)
- **NÃO PRECISA INSTALAR NADA**

#### **Passo 3: Configurar acesso remoto**

Na tela de login do executável, configure:

**Servidor API:** `http://SEU_IP_PUBLICO:8000`

---

### 🌐 Opção 2: Acesso Web (Sem instalar nada)

Se preferir acessar direto pelo navegador:

#### **No servidor (sua casa):**

1. **Habilitar acesso externo** (já está configurado no seu docker)
2. **Configurar porta forwarding** no roteador:
   - Porta externa: `443` (HTTPS)
   - Porta interna: `443`
   - IP: `192.168.15.2` (seu servidor)

3. **Obter IP público ou usar DNS dinâmico:**
   ```powershell
   # Descobrir seu IP público
   curl ifconfig.me
   ```
   
   **Ou usar serviço gratuito:**
   - [DuckDNS](https://www.duckdns.org/) (criar domínio gratuito)
   - [No-IP](https://www.noip.com/)

#### **No computador remoto (trabalho):**

Abra o navegador e acesse:
```
https://seu-dominio.duckdns.org
```

Ou:
```
https://SEU_IP_PUBLICO
```

---

### 🔐 Opção 3: VPN (Mais Seguro) - **MELHOR SEGURANÇA**

Use **Tailscale** (gratuito e fácil):

#### **Configuração:**

1. **No servidor (sua casa):**
   ```powershell
   # Instalar Tailscale
   winget install tailscale.tailscale
   
   # Criar conta e conectar
   ```

2. **No computador remoto:**
   - Instalar Tailscale
   - Fazer login com a mesma conta
   - Acessar: `http://IP_TAILSCALE:8000`

**Vantagens:**
- ✅ Criptografia ponta-a-ponta
- ✅ Não expõe servidor na internet
- ✅ Acesso seguro de qualquer lugar
- ✅ **100% Gratuito**

---

## 🚀 Como descobrir seu IP local para testes

```powershell
ipconfig
# Procure por "Endereço IPv4" (geralmente 192.168.x.x)
```

---

## 📊 Comparação das Opções

| Método | Fácil | Seguro | Requer Instalação |
|--------|-------|--------|-------------------|
| **Executável .exe** | ⭐⭐⭐ | ⭐⭐ | Não |
| **Acesso Web** | ⭐⭐⭐ | ⭐ | Não |
| **VPN (Tailscale)** | ⭐⭐ | ⭐⭐⭐ | Sim (mínima) |

---

## 💡 Recomendação Final

**Para uso casual no trabalho:**
→ Use o **executável portátil** (.exe) + configure IP do servidor

**Para uso frequente e seguro:**
→ Configure **Tailscale VPN**

**Para demonstrações/clientes:**
→ Use **acesso web** com domínio DuckDNS

---

## 🛠 Troubleshooting

### Executável não abre
- Verifique antivírus (pode bloquear)
- Execute como administrador

### Não consegue conectar ao servidor
- Verifique se o Docker está rodando em casa
- Confirme o IP público (pode mudar)
- Teste se a porta está aberta: https://www.yougetsignal.com/tools/open-ports/

### "Credenciais inválidas"
- Verifique usuário/senha
- Confirme que o servidor está acessível

---

## 📞 Suporte

Para mais ajuda, verifique os logs no terminal do Docker:
```powershell
docker-compose logs -f web
```
