import uvicorn
import threading
import streamlit as st
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
import httpx

# ========== PostgreSQL DATABASE SETUP ==========
DATABASE_URL = "postgresql://postgres:yuvi@localhost:5432/fidalex_bank"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== MODELS ==========
class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100))
    account_id = Column(String(20), unique=True)
    account_type = Column(String(20))
    balance = Column(Numeric(14, 2), default=0.00)
    transactions = relationship("Transaction", back_populates="customer")

class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    amount = Column(Numeric(14, 2))
    transaction_type = Column(String(20))  # deposit, withdraw
    transaction_time = Column(TIMESTAMP(timezone=False), server_default=func.now())
    description = Column(Text)
    customer = relationship("Customer", back_populates="transactions")

Base.metadata.create_all(bind=engine)

# ========== FASTAPI SETUP ==========
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/add_customer/")
def add_customer(name: str, acc_id: str, acc_type: str, balance: float, db: Session = Depends(get_db)):
    customer = Customer(customer_name=name, account_id=acc_id, account_type=acc_type, balance=balance)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@app.post("/add_transaction/")
def add_transaction(customer_id: int, amount: float, tx_type: str, description: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}
    
    if tx_type.lower() == "withdraw" and customer.balance < amount:
        return {"error": "Insufficient funds"}

    # Update balance
    customer.balance = customer.balance + amount if tx_type.lower() == "deposit" else customer.balance - amount
    transaction = Transaction(customer_id=customer_id, amount=amount, transaction_type=tx_type, description=description)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction

@app.get("/customers/")
def get_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()

@app.get("/transactions/")
def get_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).all()

# ========== RUN FASTAPI SERVER ==========
def run_fastapi():
    uvicorn.run(app, host="127.0.0.1", port=8000)

threading.Thread(target=run_fastapi, daemon=True).start()

# ========== STREAMLIT UI ==========
st.title("🏦 Fidalex Bank – Customer & Transaction Manager")

st.header("Add New Customer")
c_name = st.text_input("Customer Name")
c_acc_id = st.text_input("Account ID")
c_acc_type = st.selectbox("Account Type", ["savings", "current"])
c_balance = st.number_input("Initial Balance", value=0.0)
if st.button("Add Customer"):
    res = httpx.post("http://127.0.0.1:8000/add_customer/", params={
        "name": c_name, "acc_id": c_acc_id, "acc_type": c_acc_type, "balance": c_balance
    })
    st.success(f"Customer added: {res.json()}")

st.header("Add Transaction")
tx_customer_id = st.number_input("Customer ID", value=1)
tx_amount = st.number_input("Amount", value=0.0)
tx_type = st.selectbox("Transaction Type", ["deposit", "withdraw"])
tx_desc = st.text_input("Description")
if st.button("Add Transaction"):
    res = httpx.post("http://127.0.0.1:8000/add_transaction/", params={
        "customer_id": tx_customer_id, "amount": tx_amount, "tx_type": tx_type, "description": tx_desc
    })
    st.success(f"Transaction status: {res.json()}")

st.header("View All Customers")
if st.button("Show Customers"):
    res = httpx.get("http://127.0.0.1:8000/customers/")
    st.table(res.json())

st.header("View All Transactions")
if st.button("Show Transactions"):
    res = httpx.get("http://127.0.0.1:8000/transactions/")
    st.table(res.json())
