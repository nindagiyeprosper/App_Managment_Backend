from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client
from schemas import RegisterIn, LoginIn, AuthOut, UserOut
from auth import hash_password, verify_password, create_token, gen_code, get_current_user
from commissions import notifier

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(Client).filter(Client.telephone == payload.telephone).first():
        raise HTTPException(400, "Téléphone déjà utilisé")

    parrain = None
    if payload.code_parrainage:
        parrain = db.query(Client).filter(Client.code_parrainage == payload.code_parrainage).first()
        if not parrain:
            raise HTTPException(400, "Code de parrainage invalide")

    client = Client(
        nom=payload.nom, telephone=payload.telephone,
        email=payload.email, adresse=payload.adresse,
        password_hash=hash_password(payload.password),
        code_parrainage=gen_code(),
        parrain_id=parrain.id if parrain else None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    if parrain:
        current, niveau = parrain, 1
        while current and niveau <= 3:
            current.nb_descendants += 1
            db.add(current)
            if niveau < 3 and current.parrain_id:
                current = db.query(Client).get(current.parrain_id)
            else:
                current = None
            niveau += 1
        db.commit()
        notifier(db, parrain.id, "parrainage", f"Nouveau filleul : {client.nom}")
        db.commit()

    return AuthOut(token=create_token(client.id), user=client)


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.telephone == payload.telephone).first()
    if not client or not verify_password(payload.password, client.password_hash):
        raise HTTPException(401, "Téléphone ou mot de passe incorrect")
    return AuthOut(token=create_token(client.id), user=client)


@router.get("/me", response_model=UserOut)
def me(user: Client = Depends(get_current_user)):
    return user