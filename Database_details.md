# Database Details for Fidalex Bank Project

This document outlines the database architecture, technologies, and schema details for each microservice in the Fidalex Bank project. It is intended for inclusion in the project’s GitHub repository to help developers understand how data is stored, accessed, and maintained.

---

## Table of Contents

1. [Overview](#overview)
2. [Auth Service Database](#auth-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Schema: Tables & Columns
3. [Account Service Database](#account-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Schema: Tables & Columns
4. [Transaction Service Database](#transaction-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Schema: Tables & Columns
5. [Payment Service Database](#payment-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Schema: Tables & Columns
6. [Loan & Credit Service Database](#loan-amp-credit-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Schema: Tables & Columns
7. [Chatbot Service Database](#chatbot-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Collections & Fields
8. [Insights Service Database](#insights-service-database)

   * Technology & Deployment
   * Connection Details (Example)
   * Schema: Dimensions, Fact Tables & Materialized Views
9. [Shared Caching & Messaging](#shared-caching-amp-messaging)

   * Redis (Cache & Locks)
   * Kafka / RabbitMQ (Message Broker)

---

## Overview

Each microservice in Fidalex Bank has its own dedicated database (or data store), following the Database‑Per‑Service pattern. This ensures loose coupling, independent scalability, and clear ownership of data. Below are the detailed descriptions for each service’s database.

---

## Auth Service Database

### Technology & Deployment

* **Database Engine**: PostgreSQL 14+
* **Deployment**: Deployed as a Kubernetes StatefulSet (or managed RDS/PostgreSQL instance). Uses a dedicated namespace `fidalex-bank`.
* **High Availability**: Primary + 2 read replicas with streaming replication (Patroni or managed service).
* **Extensions**:

  * `pgcrypto` (for hashing/encryption)
  * Optional `pg_partman` or `pg_cron` if scheduled jobs needed

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for Auth DB credentials
apiVersion: v1
kind: Secret
metadata:
  name: auth-db-credentials
  namespace: fidalex-bank
type: Opaque
data:
  POSTGRES_USER: YXV0aF91c2Vy      # base64 for 'auth_user'
  POSTGRES_PASSWORD: c2VjdXJlUGFzcw== # base64 for 'securePass'

# Example connection string (environment variable in Auth Service Deployment)
DATABASE_URL: postgres://auth_user:securePass@auth-db.fidalex-bank.svc.cluster.local:5432/authdb
```

### Schema: Tables & Columns

1. **`users`**

   ```sql
   CREATE TABLE users (
     user_id          BIGSERIAL PRIMARY KEY,
     username         VARCHAR(50) NOT NULL UNIQUE,
     email            VARCHAR(100) NOT NULL UNIQUE,
     password_hash    TEXT NOT NULL,
     full_name        VARCHAR(150),
     phone_number     VARCHAR(20),
     is_active        BOOLEAN NOT NULL DEFAULT TRUE,
     created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE INDEX idx_users_email ON users(email);
   ```

2. **`roles`**

   ```sql
   CREATE TABLE roles (
     role_id          SMALLSERIAL PRIMARY KEY,
     role_name        VARCHAR(50) NOT NULL UNIQUE,
     description      TEXT
   );
   ```

3. **`user_roles`** (many-to-many)

   ```sql
   CREATE TABLE user_roles (
     user_id          BIGINT NOT NULL,
     role_id          SMALLINT NOT NULL,
     assigned_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     PRIMARY KEY (user_id, role_id),
     FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
     FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
   );
   ```

4. **`refresh_tokens`**

   ```sql
   CREATE TABLE refresh_tokens (
     token_id         BIGSERIAL PRIMARY KEY,
     user_id          BIGINT NOT NULL,
     token            TEXT NOT NULL UNIQUE,
     expires_at       TIMESTAMPTZ NOT NULL,
     created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     revoked          BOOLEAN NOT NULL DEFAULT FALSE,
     FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
   );

   CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
   ```

5. **`password_reset_requests`**

   ```sql
   CREATE TABLE password_reset_requests (
     request_id       BIGSERIAL PRIMARY KEY,
     user_id          BIGINT NOT NULL,
     reset_token      VARCHAR(200) NOT NULL UNIQUE,
     expires_at       TIMESTAMPTZ NOT NULL,
     created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     is_used          BOOLEAN NOT NULL DEFAULT FALSE,
     FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
   );

   CREATE INDEX idx_prr_user ON password_reset_requests(user_id);
   ```

> **Notes**:
>
> * Passwords are hashed using a strong algorithm (bcrypt/argon2) in application code.
> * Optional RLS (Row-Level Security) policies can be configured for more granular access control.

---

## Account Service Database

### Technology & Deployment

* **Database Engine**: PostgreSQL 14+
* **Deployment**: Dedicated StatefulSet (or managed DB). Multi-Availability Zone (AZ) setup.
* **Extensions**:

  * `jsonb` (for flexible address & KYC metadata)
  * `pg_partman` (optional, for helping partition large tables)
  * `pg_cron` (optional, for periodic tasks)

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for Account DB credentials
apiVersion: v1
kind: Secret
metadata:
  name: account-db-credentials
  namespace: fidalex-bank
type: Opaque
data:
  POSTGRES_USER: YWNjb3VudF91c2Vy      # base64 for 'account_user'
  POSTGRES_PASSWORD: c2VjdXJlQWNjT3A=  # base64 for 'secureAccOp'

# Environment variable in Account Service Deployment
DATABASE_URL: postgres://account_user:secureAccOp@account-db.fidalex-bank.svc.cluster.local:5432/accountdb
```

### Schema: Tables & Columns

1. **`customers`**

   ```sql
   CREATE TABLE customers (
     customer_id      BIGSERIAL PRIMARY KEY,
     first_name       VARCHAR(100) NOT NULL,
     last_name        VARCHAR(100) NOT NULL,
     date_of_birth    DATE NOT NULL,
     email            VARCHAR(100) UNIQUE,
     phone_number     VARCHAR(20),
     address          JSONB NOT NULL,        -- { "line1": "...", "city": "...", ... }
     kyc_status       VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- ENUM: PENDING, VERIFIED, REJECTED
     kyc_metadata     JSONB,                 -- { "documents": [...], "verified_by": "..." }
     created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   ALTER TABLE customers
     ADD CONSTRAINT chk_kyc_status CHECK (kyc_status IN ('PENDING','VERIFIED','REJECTED'));

   CREATE INDEX idx_customers_email ON customers(email);
   CREATE INDEX idx_customers_kyc_status ON customers(kyc_status);
   CREATE INDEX idx_customers_address_gin ON customers USING GIN (address jsonb_path_ops);
   ```

2. **`accounts`**

   ```sql
   CREATE TABLE accounts (
     account_id       BIGSERIAL PRIMARY KEY,
     customer_id      BIGINT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
     account_number   VARCHAR(20) NOT NULL UNIQUE,  -- e.g., 'FB-00012345'
     account_type     VARCHAR(20) NOT NULL,         -- ENUM: CHECKING, SAVINGS, LOAN, CREDIT
     currency         CHAR(3) NOT NULL DEFAULT 'USD',
     balance          NUMERIC(18,2) NOT NULL DEFAULT 0.00,
     status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ENUM: ACTIVE, CLOSED, FROZEN, PENDING
     opened_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     closed_at        TIMESTAMPTZ,
     updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   ALTER TABLE accounts
     ADD CONSTRAINT chk_account_type CHECK (account_type IN ('CHECKING','SAVINGS','LOAN','CREDIT')),
     ADD CONSTRAINT chk_account_status CHECK (status IN ('ACTIVE','CLOSED','FROZEN','PENDING'));

   CREATE INDEX idx_accounts_customer ON accounts(customer_id);
   CREATE INDEX idx_accounts_status ON accounts(status);
   ```

3. **`account_settings`**

   ```sql
   CREATE TABLE account_settings (
     account_id          BIGINT PRIMARY KEY REFERENCES accounts(account_id) ON DELETE CASCADE,
     overdraft_limit     NUMERIC(18,2) NOT NULL DEFAULT 0.00,
     daily_withdrawal_limit NUMERIC(18,2) NOT NULL DEFAULT 1000.00,
     notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE
   );
   ```

4. **`account_logs`** (audit trail)

   ```sql
   CREATE TABLE account_logs (
     log_id             BIGSERIAL PRIMARY KEY,
     account_id         BIGINT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
     change_type        VARCHAR(20) NOT NULL,   -- e.g., 'CREATED','UPDATED','CLOSED','BALANCE_ADJUST'
     old_value          JSONB,
     new_value          JSONB,
     changed_by         VARCHAR(100) NOT NULL,   -- e.g., 'transaction-service', 'admin'
     change_ts          TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE INDEX idx_account_logs_account ON account_logs(account_id);
   ```

> **Notes**:
>
> * Partitioning on `accounts` by `opened_at` (yearly) can be configured via `pg_partman` if table size grows significantly.
> * GIN indexes on JSONB fields accelerate queries for address subfields and KYC metadata.

---

## Transaction Service Database

### Technology & Deployment

* **Database Engine**: PostgreSQL 14+
* **Deployment**: Dedicated StatefulSet (or managed DB). Highly-available cluster.
* **Caching**: Redis Cluster for distributed locks and in-flight state.
* **Messaging**: Kafka (deployed in Kubernetes or external cluster) or RabbitMQ.
* **Extensions**:

  * `pgcrypto` (optional, for data encryption)
  * `pg_cron` (optional, for scheduled snapshots)
  * Logical replication slots for CDC to Insights.

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for Transaction DB
apiVersion: v1
kind: Secret
metadata:
  name: transaction-db-credentials
  namespace: fidalex-bank
type: Opaque
data:
  POSTGRES_USER: dHJhbnNhY3Rpb25fdXNlcg==  # base64 for 'transaction_user'
  POSTGRES_PASSWORD: c2VjdXJlVHJ4dGVk   # base64 for 'secureTrxted'

# Environment variable in Transaction Service Deployment
DATABASE_URL: postgres://transaction_user:secureTrxted@transaction-db.fidalex-bank.svc.cluster.local:5432/transactiondb
REDIS_URL: redis://redis-master.fidalex-bank.svc.cluster.local:6379/0
KAFKA_BROKERS: kafka-0.kafka.fidalex-bank.svc.cluster.local:9092,kafka-1.kafka.fidalex-bank.svc.cluster.local:9092
```

### Schema: Tables & Columns

1. **`transactions`**

   ```sql
   CREATE TABLE transactions (
     transaction_id     BIGSERIAL PRIMARY KEY,
     account_id         BIGINT NOT NULL REFERENCES accounts(account_id) ON DELETE RESTRICT,
     related_account_id BIGINT REFERENCES accounts(account_id),
     transaction_type   VARCHAR(20) NOT NULL,   -- ENUM: DEPOSIT, WITHDRAWAL, TRANSFER, FEE, REVERSAL
     amount             NUMERIC(18,2) NOT NULL,
     currency           CHAR(3) NOT NULL DEFAULT 'USD',
     status             VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- ENUM: PENDING, SUCCESS, FAILED, REVERSED
     created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     completed_at       TIMESTAMPTZ,
     description        TEXT,
     metadata           JSONB
   );

   ALTER TABLE transactions
     ADD CONSTRAINT chk_tran_type CHECK (transaction_type IN ('DEPOSIT','WITHDRAWAL','TRANSFER','FEE','REVERSAL')),
     ADD CONSTRAINT chk_tran_status CHECK (status IN ('PENDING','SUCCESS','FAILED','REVERSED'));

   CREATE INDEX idx_transactions_acc_status ON transactions(account_id, status);
   CREATE INDEX idx_transactions_created_at ON transactions(created_at);
   CREATE INDEX idx_transactions_related_acc ON transactions(related_account_id);
   ```

2. **`transaction_audit`**

   ```sql
   CREATE TABLE transaction_audit (
     audit_id           BIGSERIAL PRIMARY KEY,
     transaction_id     BIGINT NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
     audit_event        VARCHAR(20) NOT NULL,  -- 'CREATED','STATUS_UPDATED','REVERSED'
     old_status         VARCHAR(20),
     new_status         VARCHAR(20),
     changed_by         VARCHAR(100) NOT NULL,  -- 'transaction-service', 'audit-worker'
     event_ts           TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE INDEX idx_ta_transaction ON transaction_audit(transaction_id);
   ```

3. **`transaction_balance_snapshot`**

   ```sql
   CREATE TABLE transaction_balance_snapshot (
     snapshot_id        BIGSERIAL PRIMARY KEY,
     account_id         BIGINT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
     balance_snapshot   NUMERIC(18,2) NOT NULL,
     snapshot_ts        TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE INDEX idx_balance_snapshot_acc_time ON transaction_balance_snapshot(account_id, snapshot_ts);
   ```

> **Notes**:
>
> * Use **SELECT … FOR UPDATE** or **pg\_advisory\_xact\_lock(account\_id)** to serialize balance updates.
> * Configure logical replication for streaming changes to the Insights Service.
> * Redis locks keyed by `lock:acct:{account_id}` prevent concurrent modifications.

---

## Payment Service Database

### Technology & Deployment

* **Database Engine**: PostgreSQL 14+
* **Deployment**: Dedicated StatefulSet or managed instance, highly available.
* **Caching**: Redis for idempotency keys and rate-limiting.
* **Messaging**: Kafka / RabbitMQ for async event publication.
* **Extensions**: `pg_cron` (optional, for scheduled payment jobs)

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for Payment DB
apiVersion: v1
kind: Secret
metadata:
  name: payment-db-credentials
  namespace: fidalex-bank
type: Opaque
data:
  POSTGRES_USER: cGF5bWVudF91c2Vy   # base64 for 'payment_user'
  POSTGRES_PASSWORD: c2VjcmVQYXlt # base64 for 'secrePaym'

# Environment variable in Payment Service Deployment
DATABASE_URL: postgres://payment_user:secrePaym@payment-db.fidalex-bank.svc.cluster.local:5432/paymentdb
REDIS_URL: redis://redis-master.fidalex-bank.svc.cluster.local:6379/1
KAFKA_BROKERS: kafka-0.kafka.fidalex-bank.svc.cluster.local:9092,kafka-1.kafka.fidalex-bank.svc.cluster.local:9092
```

### Schema: Tables & Columns

1. **`payments`**

   ```sql
   CREATE TABLE payments (
     payment_id         BIGSERIAL PRIMARY KEY,
     account_id         BIGINT NOT NULL REFERENCES accounts(account_id) ON DELETE RESTRICT,
     external_reference VARCHAR(100),    -- e.g. 'STRIPE_CHG_abc123'
     payment_method     VARCHAR(20) NOT NULL,  -- ENUM: ACH, WIRE, CARD, EXTERNAL
     amount             NUMERIC(18,2) NOT NULL,
     currency           CHAR(3) NOT NULL DEFAULT 'USD',
     status             VARCHAR(20) NOT NULL DEFAULT 'INITIATED',  -- ENUM: INITIATED, PENDING, COMPLETED, FAILED, REVERSED
     initiated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     completed_at       TIMESTAMPTZ,
     metadata           JSONB,
     UNIQUE (account_id, external_reference)
   );

   ALTER TABLE payments
     ADD CONSTRAINT chk_payment_method CHECK (payment_method IN ('ACH','WIRE','CARD','EXTERNAL')),
     ADD CONSTRAINT chk_payment_status CHECK (status IN ('INITIATED','PENDING','COMPLETED','FAILED','REVERSED'));

   CREATE INDEX idx_payments_acc_status ON payments(account_id, status);
   CREATE INDEX idx_payments_initiated_at ON payments(initiated_at);
   ```

2. **`payment_attempts`**

   ```sql
   CREATE TABLE payment_attempts (
     attempt_id         BIGSERIAL PRIMARY KEY,
     payment_id         BIGINT NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
     attempt_ts         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     status             VARCHAR(20) NOT NULL,   -- 'REQUESTED','PROCESSING','SUCCESS','FAILED'
     response_code      VARCHAR(50),
     response_message   TEXT
   );

   CREATE INDEX idx_pa_payment ON payment_attempts(payment_id);
   ```

3. **`scheduled_payments`**

   ```sql
   CREATE TABLE scheduled_payments (
     schedule_id        BIGSERIAL PRIMARY KEY,
     account_id         BIGINT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
     amount             NUMERIC(18,2) NOT NULL,
     currency           CHAR(3) NOT NULL DEFAULT 'USD',
     frequency          VARCHAR(10) NOT NULL,  -- ENUM: DAILY, WEEKLY, MONTHLY, YEARLY
     next_run_date      DATE NOT NULL,
     end_date           DATE,
     is_active          BOOLEAN NOT NULL DEFAULT TRUE,
     created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   ALTER TABLE scheduled_payments
     ADD CONSTRAINT chk_sp_frequency CHECK (frequency IN ('DAILY','WEEKLY','MONTHLY','YEARLY'));

   CREATE INDEX idx_sp_acc_date ON scheduled_payments(account_id, next_run_date);
   ```

> **Notes**:
>
> * Partition `scheduled_payments` by year if retention is long.
> * Unique index on `(account_id, external_reference)` ensures idempotent API calls.
> * Redis stores idempotency keys: `payment:idempotency:{account_id}:{external_reference}`.

---

## Loan & Credit Service Database

### Technology & Deployment

* **Database Engine**: PostgreSQL 14+
* **Deployment**: StatefulSet with primary + replicas. Multi-AZ for HA.
* **Caching**: Redis for ML feature vector caching.
* **Messaging**: Kafka / RabbitMQ for events (e.g., `loan.decided`).
* **Extensions**:

  * `jsonb` (for raw credit report data)
  * `pg_partman` (optional, for partitioning large tables)
  * `pg_cron` (optional, for scheduled tasks)

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for Loan DB
apiVersion: v1
kind: Secret
metadata:
  name: loan-db-credentials
  namespace: fidalex-bank
type: Opaque
data:
  POSTGRES_USER: bG9hbl91c2Vy    # base64 for 'loan_user'
  POSTGRES_PASSWORD: bG9hbiUwMmxw  # base64 for 'loan@02lp'

# Environment variable in Loan & Credit Service Deployment
DATABASE_URL: postgres://loan_user:loan@02lp@loan-db.fidalex-bank.svc.cluster.local:5432/loandb
REDIS_URL: redis://redis-master.fidalex-bank.svc.cluster.local:6379/2
KAFKA_BROKERS: kafka-0.kafka.fidalex-bank.svc.cluster.local:9092,kafka-1.kafka.fidalex-bank.svc.cluster.local:9092
```

### Schema: Tables & Columns

1. **`loan_applications`**

   ```sql
   CREATE TABLE loan_applications (
     application_id     BIGSERIAL PRIMARY KEY,
     customer_id        BIGINT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
     amount_requested   NUMERIC(18,2) NOT NULL,
     term_months        INT NOT NULL,
     purpose            TEXT,
     status             VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',  -- ENUM: SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED
     submitted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     reviewed_at        TIMESTAMPTZ,
     decision_by        VARCHAR(100)
   );

   ALTER TABLE loan_applications
     ADD CONSTRAINT chk_la_status CHECK (status IN ('SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED'));

   CREATE INDEX idx_la_cust_status ON loan_applications(customer_id, status);
   ```

2. **`loan_accounts`**

   ```sql
   CREATE TABLE loan_accounts (
     loan_id            BIGSERIAL PRIMARY KEY,
     application_id     BIGINT NOT NULL UNIQUE REFERENCES loan_applications(application_id) ON DELETE CASCADE,
     customer_id        BIGINT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
     principal_amount   NUMERIC(18,2) NOT NULL,
     outstanding_balance NUMERIC(18,2) NOT NULL,
     interest_rate      NUMERIC(5,3) NOT NULL,
     start_date         DATE NOT NULL,
     end_date           DATE NOT NULL,
     status             VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ENUM: ACTIVE, CLOSED, DEFAULTED
     created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   ALTER TABLE loan_accounts
     ADD CONSTRAINT chk_la_acc_status CHECK (status IN ('ACTIVE','CLOSED','DEFAULTED'));

   CREATE INDEX idx_la_loan_cust ON loan_accounts(customer_id);
   ```

3. **`loan_payments`**

   ```sql
   CREATE TABLE loan_payments (
     payment_id         BIGSERIAL PRIMARY KEY,
     loan_id            BIGINT NOT NULL REFERENCES loan_accounts(loan_id) ON DELETE CASCADE,
     due_date           DATE NOT NULL,
     payment_amount     NUMERIC(18,2) NOT NULL,
     paid_amount        NUMERIC(18,2) NOT NULL DEFAULT 0.00,
     paid_date          DATE,
     status             VARCHAR(20) NOT NULL DEFAULT 'DUE'  -- ENUM: DUE, PAID, LATE, DEFAULTED
   );

   ALTER TABLE loan_payments
     ADD CONSTRAINT chk_lp_status CHECK (status IN ('DUE','PAID','LATE','DEFAULTED'));

   CREATE INDEX idx_lp_loan_due ON loan_payments(loan_id, due_date);
   ```

4. **`credit_reports`**

   ```sql
   CREATE TABLE credit_reports (
     report_id          BIGSERIAL PRIMARY KEY,
     customer_id        BIGINT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
     report_source      VARCHAR(100) NOT NULL,  -- e.g., 'Experian', 'TransUnion'
     fetched_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     report_data        JSONB NOT NULL
   );

   CREATE INDEX idx_cr_cust ON credit_reports(customer_id);
   CREATE INDEX idx_cr_source ON credit_reports(report_source);
   CREATE INDEX idx_cr_report_data_gin ON credit_reports USING GIN (report_data jsonb_path_ops);
   ```

5. **`loan_decision_logs`**

   ```sql
   CREATE TABLE loan_decision_logs (
     log_id             BIGSERIAL PRIMARY KEY,
     application_id     BIGINT NOT NULL REFERENCES loan_applications(application_id) ON DELETE CASCADE,
     decision           VARCHAR(20) NOT NULL,  -- 'AUTO_APPROVED','AUTO_REJECTED','MANUAL_APPROVED','MANUAL_REJECTED'
     decision_by        VARCHAR(100) NOT NULL,  -- e.g. 'ML_MODEL_V1','underwriter_123'
     decision_score     NUMERIC(5,2),           -- e.g. 720.45
     comments           TEXT,
     decision_ts        TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE INDEX idx_ldl_app ON loan_decision_logs(application_id);
   ```

> **Notes**:
>
> * Triggers (PL/pgSQL) can automatically move approved applications into `loan_accounts`.
> * Partition `credit_reports` by `fetched_at` (monthly/yearly) if very high volume.
> * Redis key pattern: `loan:features:{customer_id}` for cached ML feature vectors.

---

## Chatbot Service Database

### Technology & Deployment

* **Database Engine**: MongoDB (Replica Set for HA)
* **Deployment**: Deployed in Kubernetes as a StatefulSet or managed Atlas cluster.
* **Caching**: Redis Cluster for session state (in-memory).

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for MongoDB connection
apiVersion: v1
kind: Secret
metadata:
  name: chatbot-mongo-credentials
  namespace: fidalex-bank
type: Opaque
data:
  MONGO_URI: 'bW9uZ29kYjovL2NodGFib3Q6c2VjdXJlQChfdXNlcigxMjM='  # base64 for 'mongodb://chatbot:secure@(mongo-host:27017)/chatbotdb'

# Environment variable in Chatbot Service Deployment
MONGO_URI: mongodb://chatbot:secure@chatbot-mongo-0.chatbot-mongo.fidalex-bank.svc.cluster.local:27017/chatbotdb
REDIS_URL: redis://redis-master.fidalex-bank.svc.cluster.local:6379/3
```

### Collections & Fields

1. **`conversations`**

   ```json
   {
     "_id": ObjectId,
     "conversation_id": "conv-abcdef12345",  
     "user_id": 12345,
     "started_at": ISODate("2025-06-01T14:30:00Z"),
     "ended_at": ISODate("2025-06-01T14:45:00Z"),  
     "metadata": {
       "device": "web", "location": "NYC", "intent_detected": "account_balance"
     }
   }
   ```

2. **`messages`**

   ```json
   {
     "_id": ObjectId,
     "message_id": "msg-xyz987",
     "conversation_id": "conv-abcdef12345",  
     "sender_type": "USER" | "BOT",
     "message_text": "What is my checking account balance?",
     "timestamp": ISODate("2025-06-01T14:31:00Z"),
     "nlp_metadata": {
       "intent": "get_account_balance",
       "entities": { "account_type": "checking" },
       "confidence": 0.92
     }
   }
   ```

3. **`intents`**

   ```json
   {
     "_id": "intent_get_balance",
     "name": "get_account_balance",
     "training_phrases": [
       "What is my balance?",
       "How much money do I have in my checking account?",
       "Show me my account balance",
       "..."
     ],
     "response_templates": [
       "Your {account_type} account balance is ${balance}.",
       "Current balance: ${balance} in your {account_type} account.",
       "..."
     ],
     "created_at": ISODate("2025-06-01T12:00:00Z"),
     "updated_at": ISODate("2025-06-02T08:15:00Z")
   }
   ```

4. **`embeddings`** (optional)

   ```json
   {
     "_id": ObjectId,
     "text_chunk": "I want to transfer $500 to savings.",
     "vector": [0.023, -0.112, 0.895, ...],   
     "created_at": ISODate("2025-06-01T14:25:00Z")
   }
   ```

> **Notes**:
>
> * Use a **2dsphere** index on `embeddings.vector` if performing approximate nearest‐neighbor (ANN) searches (MongoDB 6.x+).
> * Redis key pattern: `session:{conversation_id}` stores ephemeral context (serialized JSON) with TTL.

---

## Insights Service Database

### Technology & Deployment

* **Database Engine**: PostgreSQL 14+ (with TimescaleDB extension or Citus/pg\_partman for partitioning).
* **Deployment**: StatefulSet or managed Postgres (e.g., GCP Cloud SQL, AWS Aurora).
* **Extensions**:

  * `timescaledb` (optional, for time-series optimization)
  * `pg_partman` (for automated partitioning)
  * `pg_cron` (for scheduled materialized view refreshes)
  * `postgres_fdw` (if joining remote tables)
* **Event Ingestion**: Uses logical replication or a Kafka Consumer job to load data from OLTP services.

### Connection Details (Example)

```yaml
# Example Kubernetes Secret for Insights DB
apiVersion: v1
kind: Secret
metadata:
  name: insights-db-credentials
  namespace: fidalex-bank
type: Opaque
data:
  POSTGRES_USER: aW5zaWdodHNfdXNlcg==  # base64 for 'insights_user'
  POSTGRES_PASSWORD: aW5zaWdodFNlY3JldA== # base64 for 'insightsSecret'

# Environment variable in Insights Service Deployment
DATABASE_URL: postgres://insights_user:insightsSecret@insights-db.fidalex-bank.svc.cluster.local:5432/insightsdb
```

### Schema: Dimensions, Fact Tables & Materialized Views

#### 1. Dimension Tables

1. **`dim_date`** (pre-populated calendar table)

   ```sql
   CREATE TABLE dim_date (
     date_id           DATE PRIMARY KEY,
     year              SMALLINT NOT NULL,
     quarter           SMALLINT NOT NULL,
     month             SMALLINT NOT NULL,
     day               SMALLINT NOT NULL,
     day_of_week       SMALLINT NOT NULL
   );
   -- Populate this table via a generate_series script (2000–2050).
   ```

2. **`dim_account`** (denormalized subset from Account Service)

   ```sql
   CREATE TABLE dim_account (
     account_id        BIGINT PRIMARY KEY,   -- from accounts.account_id
     customer_id       BIGINT NOT NULL,
     account_type      VARCHAR(20) NOT NULL,
     opened_year       SMALLINT NOT NULL,
     status            VARCHAR(20) NOT NULL
   );

   CREATE INDEX idx_dim_account_cust ON dim_account(customer_id);
   ```

3. **`dim_branch`** (if applicable)

   ```sql
   CREATE TABLE dim_branch (
     branch_id         INT PRIMARY KEY,
     branch_name       VARCHAR(100) NOT NULL,
     region            VARCHAR(50) NOT NULL
   );
   ```

#### 2. Fact Tables (Partitioned)

1. **`fact_transactions`**

   ```sql
   CREATE TABLE fact_transactions (
     transaction_id     BIGINT NOT NULL PRIMARY KEY,
     account_id         BIGINT NOT NULL,
     branch_id          INT NOT NULL,
     date_id            DATE NOT NULL,
     amount             NUMERIC(18,2) NOT NULL,
     transaction_type   VARCHAR(20) NOT NULL,
     status             VARCHAR(20) NOT NULL
   ) PARTITION BY RANGE (date_id);

   -- Example partitions (quarterly)
   CREATE TABLE fact_transactions_2025q1 PARTITION OF fact_transactions
     FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
   CREATE TABLE fact_transactions_2025q2 PARTITION OF fact_transactions
     FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');
   -- ... more partitions as needed.

   CREATE INDEX idx_ft_account_date ON fact_transactions(account_id, date_id);
   CREATE INDEX idx_ft_branch_date ON fact_transactions(branch_id, date_id);
   ```

2. **`fact_account_balance`**

   ```sql
   CREATE TABLE fact_account_balance (
     snapshot_id        BIGSERIAL PRIMARY KEY,
     account_id         BIGINT NOT NULL,
     date_id            DATE NOT NULL,
     balance            NUMERIC(18,2) NOT NULL
   ) PARTITION BY RANGE (date_id);

   CREATE TABLE fact_account_balance_2025 PARTITION OF fact_account_balance
     FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
   -- Additional yearly/monthly partitions.

   CREATE INDEX idx_fab_acc_date ON fact_account_balance(account_id, date_id);
   ```

#### 3. Materialized Views / Aggregations

1. **`mv_daily_branch_summary`**

   ```sql
   CREATE MATERIALIZED VIEW mv_daily_branch_summary AS
   SELECT
     ft.date_id,
     ft.branch_id,
     COUNT(ft.transaction_id)                    AS total_transactions,
     SUM(ft.amount)                              AS total_volume,
     SUM(CASE WHEN ft.status = 'SUCCESS' THEN ft.amount ELSE 0 END) AS total_success_volume
   FROM fact_transactions ft
   GROUP BY ft.date_id, ft.branch_id;

   CREATE INDEX idx_mv_dbs_date_branch ON mv_daily_branch_summary(date_id, branch_id);
   ```

2. **Refresh Strategy**

   * Use `pg_cron` or an external Kubernetes CronJob to periodically (nightly) run:

     ```sql
     REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_branch_summary;
     ```

> **Notes**:
>
> * Ingestion pipelines (e.g., a small Go/Python worker) subscribe to Kafka topics (`transaction.completed`, `payment.processed`, `loan.decided`) and `INSERT` into the corresponding partition of `fact_transactions`, `fact_account_balance`, etc.
> * Alternatively, configure **logical replication** from OLTP Postgres instances into this Analytics DB.

---

## Shared Caching & Messaging

### Redis (Cache & Locks)

* **Cluster**: Redis Sentinel or Redis Cluster deployed in Kubernetes (3+ nodes for HA).
* **Databases / Key Patterns**:

  * **Auth Service**: (none)
  * **Account Service**: (none)
  * **Transaction Service**:

    * Locks: `lock:acct:{account_id}` (short TTL advisory lock for fund transfers)
    * Pending Flags: `txn:pending:{transaction_id}`
  * **Payment Service**:

    * Idempotency: `payment:idempotency:{account_id}:{external_reference}`
    * Rate Limiting (optional): `rl:payment:{account_id}` with sliding window counters
  * **Loan & Credit Service**:

    * ML Feature Cache: `loan:features:{customer_id}` → JSON serialized feature vector
    * Session Locks (rare)
  * **Chatbot Service**:

    * Session State: `session:{conversation_id}` → JSON containing context, intent, entities
    * Rate Limiting: `rl:chat:{conversation_id}`
  * **Insights Service**: (none directly; maybe caching recent summary queries)

### Kafka / RabbitMQ (Message Broker)

* **Cluster**: Deployed in Kubernetes (Kafka: 3+ brokers; RabbitMQ: 3-node cluster) or external managed service.
* **Topics / Queues**:

  * `transaction.completed`:

    * Payload: `{ transaction_id, account_id, related_account_id, amount, currency, timestamp, status }`
    * Consumers: Insights Service, possibly Loan Service (for credit utilization changes)
  * `payment.processed`:

    * Payload: `{ payment_id, account_id, amount, currency, timestamp, status }`
    * Consumers: Insights Service
  * `loan.decided`:

    * Payload: `{ application_id, customer_id, status, decision_score, timestamp }`
    * Consumers: Account Service (to create loan account), Insights Service
  * `customer.updated` (optional):

    * Payload: `{ customer_id, change_type, updated_fields, timestamp }`
    * Consumers: Chatbot Service, Insights Service

> **Note**: When using **Kafka**, ensure topic retention and replication factor are configured for durability (e.g., replication factor = 3, retention = 7d). If using **RabbitMQ**, configure mirrored queues and high‑availability policies accordingly.

---

## Summary & Best Practices

1. **Database‑Per‑Service**: Each microservice owns its own database or data store. No direct cross-service SQL joins—communication is via APIs or asynchronous messages.
2. **Polyglot Persistence**: Although we standardized on PostgreSQL for relational data, we still leverage Redis and MongoDB for specialized use cases (caching, locks, document storage, session state).
3. **PostgreSQL Features**:

   * **JSONB** for semi-structured data (addresses, KYC metadata, raw credit reports).
   * **Partitioning** for large, time‑series tables (`fact_transactions`, `scheduled_payments`, etc.).
   * **Logical Replication** or **CDC (e.g., Debezium)** to feed the Analytics DB.
   * **Extensions**: `pgcrypto`, `timescaledb` (optional), `pg_partman`, `pg_cron`.
4. **Security & Compliance**:

   * TLS encryption between services and databases.
   * Least‑privilege user accounts for each database.
   * Optionally, Row‑Level Security (RLS) for exceptionally sensitive tables.
   * Regular backups and point-in-time recovery (PITR).
5. **Scalability & HA**:

   * Each PostgreSQL is deployed as a primary + replicas (or in a managed high-availability cluster).
   * Redis and Kafka/RabbitMQ are clustered for high availability.
   * ConfigServer/SecretsManager and ServiceMesh add resilience and security.
6. **Observability**:

   * Use Prometheus/Grafana for metrics.
   * Use Fluentd/Kibana for centralized logs.
   * Use Jaeger/OpenTelemetry for distributed tracing.

---

*End of Database\_details.md*




| **Service**               | **Key APIs / Endpoints**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | **Database(s) Used**                                                                                                                          | **Data Stored**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auth Service**          | • `POST /auth/register`  – Create new user<br>• `POST /auth/login`  – Authenticate & issue JWT<br>• `POST /auth/refresh`  – Refresh JWT<br>• `POST /auth/logout`  – Revoke refresh token<br>• `GET /auth/me`  – Get current user profile (via JWT)                                                                                                                                                                                                                                                                                           | **PostgreSQL 14+**<br>(auth-db)                                                                                                               | • `users` ( user\_id, username, email, password\_hash, full\_name, phone\_number, is\_active, created\_at, updated\_at )<br>• `roles` ( role\_id, role\_name, description )<br>• `user_roles` ( user\_id ↔ role\_id, assigned\_at )<br>• `refresh_tokens` ( token\_id, user\_id, token, expires\_at, revoked, created\_at )<br>• `password_reset_requests` ( request\_id, user\_id, reset\_token, expires\_at, is\_used, created\_at )                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Account Service**       | • `GET /customers`  – List all customers<br>• `GET /customers/{id}`  – Fetch customer details<br>• `POST /customers`  – Create new customer<br>• `PUT /customers/{id}`  – Update customer data<br>• `GET /accounts/{id}`  – Fetch account metadata/balance<br>• `POST /accounts`  – Open new account<br>• `PUT /accounts/{id}`  – Update account status (e.g., freeze/close)<br>• `GET /accounts/{id}/balance`  – Current balance<br>• `GET /accounts/{id}/settings`  – Fetch per-account config                                             | **PostgreSQL 14+**<br>(account-db)                                                                                                            | • `customers` ( customer\_id, first\_name, last\_name, date\_of\_birth, email, phone\_number, address (JSONB), kyc\_status, kyc\_metadata (JSONB), created\_at, updated\_at )<br>• `accounts` ( account\_id, customer\_id → customers, account\_number, account\_type, currency, balance, status, opened\_at, closed\_at, updated\_at )<br>• `account_settings` ( account\_id → accounts, overdraft\_limit, daily\_withdrawal\_limit, notifications\_enabled )<br>• `account_logs` ( log\_id, account\_id → accounts, change\_type, old\_value (JSONB), new\_value (JSONB), changed\_by, change\_ts )                                                                                                                                                                                                                                                                               |
| **Transaction Service**   | • `POST /transactions/transfer`  – Transfer between accounts<br>• `GET /transactions/{id}`  – Fetch single transaction<br>• `GET /accounts/{id}/transactions`  – List paged transactions for account<br>• `GET /transactions?status={status}&date_from={…}&…`  – Filtered search                                                                                                                                                                                                                                                             | **PostgreSQL 14+**<br>(transaction-db)<br>**Redis**<br>(distributed locks, “pending” flags)<br>**Kafka / RabbitMQ**<br>(for event publishing) | • `transactions` ( transaction\_id, account\_id → accounts, related\_account\_id → accounts, transaction\_type, amount, currency, status, created\_at, completed\_at, description, metadata (JSONB) )<br>• `transaction_audit` ( audit\_id, transaction\_id → transactions, audit\_event, old\_status, new\_status, changed\_by, event\_ts )<br>• `transaction_balance_snapshot` ( snapshot\_id, account\_id → accounts, balance\_snapshot, snapshot\_ts )<br>• **Redis** stores ephemeral locks keyed by `lock:acct:{account_id}` during in-flight transfers                                                                                                                                                                                                                                                                                                                       |
| **Payment Service**       | • `POST /payments`  – Initiate one-off payment (ACH/Wire/Card)<br>• `GET /payments/{id}`  – Fetch payment status<br>• `GET /accounts/{id}/payments`  – List payments for an account<br>• `POST /payments/schedule`  – Create/Update scheduled payment<br>• `GET /payments/scheduled/{schedule_id}`  – Fetch schedule<br>• `DELETE /payments/schedule/{schedule_id}`  – Cancel schedule                                                                                                                                                       | **PostgreSQL 14+**<br>(payment-db)<br>**Redis**<br>(idempotency, rate-limiting)<br>**Kafka / RabbitMQ**<br>(event publishing)                 | • `payments` ( payment\_id, account\_id → accounts, external\_reference (unique), payment\_method, amount, currency, status, initiated\_at, completed\_at, metadata (JSONB) )<br>• `payment_attempts` ( attempt\_id, payment\_id → payments, attempt\_ts, status, response\_code, response\_message )<br>• `scheduled_payments` ( schedule\_id, account\_id → accounts, amount, currency, frequency, next\_run\_date, end\_date, is\_active, created\_at, updated\_at )<br>• **Redis** stores idempotency keys keyed by `payment:idempotency:{account_id}:{external_reference}`                                                                                                                                                                                                                                                                                                     |
| **Loan & Credit Service** | • `POST /loans/apply`  – Submit new loan application<br>• `GET /loans/applications/{id}`  – Fetch application<br>• `GET /loans/customers/{customer_id}/applications`  – List customer’s applications<br>• `GET /loans/{loan_id}`  – Fetch active loan account<br>• `GET /loans/{loan_id}/payments`  – Payment schedule/status<br>• `POST /loans/{loan_id}/pay`  – Make a loan installment payment<br>• `GET /creditscore/{customer_id}`  – Fetch latest credit score<br>• `GET /creditreports/{customer_id}`  – Fetch raw credit report JSON | **PostgreSQL 14+**<br>(loan-db)<br>**Redis**<br>(ML feature cache)<br>**Kafka / RabbitMQ**<br>(event publishing)                              | • `loan_applications` ( application\_id, customer\_id → customers, amount\_requested, term\_months, purpose, status, submitted\_at, reviewed\_at, decision\_by )<br>• `loan_accounts` ( loan\_id, application\_id → loan\_applications, customer\_id → customers, principal\_amount, outstanding\_balance, interest\_rate, start\_date, end\_date, status, created\_at, updated\_at )<br>• `loan_payments` ( payment\_id, loan\_id → loan\_accounts, due\_date, payment\_amount, paid\_amount, paid\_date, status )<br>• `credit_reports` ( report\_id, customer\_id → customers, report\_source, fetched\_at, report\_data (JSONB) )<br>• `loan_decision_logs` ( log\_id, application\_id → loan\_applications, decision, decision\_by, decision\_score, comments, decision\_ts )<br>• **Redis** key `loan:features:{customer_id}` holds serialized feature vectors for ML scoring |
| **Chatbot Service**       | • `POST /chat/start`  – Begin new conversation (returns conversation\_id)<br>• `POST /chat/message`  – Send user message, get bot response<br>• `GET /chat/{conversation_id}/messages`  – List message history<br>• `GET /intents`  – List registered intents<br>• `POST /intents`  – Create/update intent training data<br>• `GET /embeddings/{text}`  – Return vector embedding for text (optional)                                                                                                                                        | **MongoDB Replica Set**<br>(chatbot-db)<br>**Redis**<br>(session state, rate-limiting)                                                        | • `conversations` ( \_id / conversation\_id, user\_id, started\_at, ended\_at, metadata )<br>• `messages` ( \_id / message\_id, conversation\_id → conversations, sender\_type (USER/BOT), message\_text, timestamp, nlp\_metadata (JSON) )<br>• `intents` ( \_id, name, training\_phrases \[ … ], response\_templates \[ … ], created\_at, updated\_at )<br>• `embeddings` ( \_id, text\_chunk, vector \[array of floats], created\_at )<br>• **Redis** stores ephemeral session context keyed by `session:{conversation_id}`                                                                                                                                                                                                                                                                                                                                                      |
| **Insights Service**      | • `GET /analytics/daily-summary?date={YYYY-MM-DD}`  – Daily txn/volume per branch<br>• `GET /analytics/transactions?start={…}&end={…}&branch_id={…}`  – Filtered TXN facts<br>• `GET /analytics/accounts-report?date={YYYY-MM-DD}`  – Account balance snapshots<br>• `GET /analytics/loans-report?start={…}&end={…}`  – Loan disbursal & payment stats<br>• `GET /analytics/customers-growth?start={…}&end={…}`  – New customer sign-ups                                                                                                     | **PostgreSQL 14+**<br>(analytics-db)<br> – Partitioned tables<br> – Materialized views (pg\_cron scheduled refresh)                           | • `dim_date` ( date\_id, year, quarter, month, day, day\_of\_week ) – prepopulated calendar table<br>• `dim_account` ( account\_id, customer\_id, account\_type, opened\_year, status ) – denormalized from `accounts`<br>• `dim_branch` ( branch\_id, branch\_name, region ) – if branch data exists<br>• `fact_transactions` ( transaction\_id, account\_id, branch\_id, date\_id, amount, transaction\_type, status ) – partitioned by `date_id`<br>• `fact_account_balance` ( snapshot\_id, account\_id, date\_id, balance ) – partitioned by `date_id`<br>• Materialized views (e.g., `mv_daily_branch_summary`) storing pre‐aggregated metrics<br>• ETL logs / CDC offsets (internal tracking tables)                                                                                                                                                                         |


