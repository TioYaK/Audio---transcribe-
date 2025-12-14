import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

def seed_rules():
    db = SessionLocal()
    
    # Define rules based on CONTEXTO_PRODUTO.md
    new_rules = [
        {
            "name": "Conformidade Bradesco (Positivo)",
            "category": "positive",
            "keywords": "economia programada, 60 meses, resgate, sorteio, número da sorte, portal proteção, 0800, vigência, carência 12 meses, IPCA, chances de ganhar, título de capitalização",
            "description": "Termos obrigatórios e características positivas do produto Bradesco Capitalização."
        },
        {
            "name": "Atenção Operacional (Neutro/Risco Baixo)",
            "category": "negative", # Maps to Yellow/Orange in UI
            "keywords": "débito automático, reajuste anual, imposto de renda, não renova, cancelamento, 30% ir, débito na fatura",
            "description": "Pontos de atenção que devem ser explicados corretamente ao cliente."
        },
        {
            "name": "Risco Crítico / Fraude",
            "category": "critical", # Maps to Red in UI
            "keywords": "garantido, investimento, rendimento, sem risco, obrigatório, pressão, urgência falsa, omissão, poupança, aplicação financeira",
            "description": "Termos proibidos ou que indicam venda incorreta/agressiva (Misselling)."
        }
    ]

    print("Checking existing rules...")
    for rule_data in new_rules:
        # Check if rule with same name exists
        existing = db.query(models.AnalysisRule).filter(models.AnalysisRule.name == rule_data["name"]).first()
        if existing:
            print(f"Updating rule: {rule_data['name']}")
            existing.category = rule_data["category"]
            existing.keywords = rule_data["keywords"]
            existing.description = rule_data["description"]
            existing.is_active = True
        else:
            print(f"Creating rule: {rule_data['name']}")
            new_rule = models.AnalysisRule(
                name=rule_data["name"],
                category=rule_data["category"],
                keywords=rule_data["keywords"],
                description=rule_data["description"],
                is_active=True
            )
            db.add(new_rule)
    
    db.commit()
    print("Rules seeded successfully!")
    db.close()

if __name__ == "__main__":
    seed_rules()
