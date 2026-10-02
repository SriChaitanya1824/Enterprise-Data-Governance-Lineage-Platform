from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.common import Page, Size, get_record, page_records, validate_references
from app.core.security import DB, User, authorize, passwords, token_for
from app.models.entities import (
    BusinessDomain,
    Person,
)
from app.schemas.requests import (
    DomainInput,
    Login,
    UserCreate,
    UserPatch,
)
from app.schemas.responses import PageResponse, RecordResponse
from app.services.audit import audit, serialize

router = APIRouter(prefix="/api", tags=["identity"])

DUMMY_HASH = passwords.hash("unusable-dummy-password-value")


@router.post("/auth/login")
def login(data: Login, db: DB):
    user = db.scalar(select(Person).where(Person.email == data.email))
    # Verify against a dummy hash when the account does not exist, limiting timing differences.

    valid = passwords.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Invalid credentials")
    audit(db, user, "Signed in", user)
    return {"access_token": token_for(user), "token_type": "bearer", "user": serialize(user)}


@router.get("/auth/me")
def me(user: User):
    return serialize(user)


@router.get("/users", response_model=PageResponse[RecordResponse])
def users(db: DB, user: User, page: Page = 1, page_size: Size = 100):
    return page_records(db, select(Person).order_by(Person.name), page, page_size)


@router.post("/users", status_code=201)
def create_user(data: UserCreate, db: DB, user: User):
    authorize(user)
    validate_references(db, data)
    record = Person(
        **data.model_dump(exclude={"password"}), password_hash=passwords.hash(data.password)
    )
    db.add(record)
    audit(db, user, "User created", record)
    return serialize(record)


@router.get("/domains", response_model=PageResponse[RecordResponse])
def domains(db: DB, user: User, page: Page = 1, page_size: Size = 100):
    return page_records(db, select(BusinessDomain).order_by(BusinessDomain.name), page, page_size)


@router.post("/domains", status_code=201)
def create_domain(data: DomainInput, db: DB, user: User):
    authorize(user)
    record = BusinessDomain(**data.model_dump())
    db.add(record)
    audit(db, user, "Domain created", record)
    return serialize(record)


@router.patch("/users/{id}")
def update_user(id: int, data: "UserPatch", db: DB, user: User):
    authorize(user)
    record = get_record(db, Person, id)
    changes = data.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(422, "User attributes cannot be null")
    if id == user.id and (
        changes.get("active") is False or changes.get("role", "ADMIN") != "ADMIN"
    ):
        raise HTTPException(409, "An administrator cannot revoke their own access")
    before = serialize(record)
    for key, value in changes.items():
        setattr(record, key, value)
    audit(db, user, "Stakeholder access updated", record, before)
    return serialize(record)
