#!/bin/bash
# ============================================
# Script de Criptografia de Backups
# ============================================
# Criptografa backups do PostgreSQL com GPG

BACKUP_DIR="./backups"
PASSPHRASE_FILE="./secrets/backup_passphrase.txt"

if [ ! -f "$PASSPHRASE_FILE" ]; then
    echo "❌ Arquivo de passphrase não encontrado: $PASSPHRASE_FILE"
    exit 1
fi

echo "🔐 Criptografando backups..."

for file in "$BACKUP_DIR"/*.sql.gz; do
    if [ -f "$file" ] && [ ! -f "$file.gpg" ]; then
        echo "📦 Criptografando: $(basename "$file")"
        gpg --symmetric \
            --cipher-algo AES256 \
            --batch \
            --yes \
            --passphrase-file "$PASSPHRASE_FILE" \
            --output "$file.gpg" \
            "$file"
        
        if [ $? -eq 0 ]; then
            echo "✅ Criptografado: $(basename "$file.gpg")"
            rm "$file"  # Remove arquivo não criptografado
        else
            echo "❌ Erro ao criptografar: $(basename "$file")"
        fi
    fi
done

echo "✨ Criptografia completa!"
