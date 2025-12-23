from app.database import SessionLocal
from app import models

db = SessionLocal()

# Remove usuário indesejado
user = db.query(models.User).filter(models.User.username == '123123123123').first()
if user:
    db.delete(user)
    db.commit()
    print('Usuario 123123123123 removido com sucesso')
else:
    print('Usuario nao encontrado')

db.close()
