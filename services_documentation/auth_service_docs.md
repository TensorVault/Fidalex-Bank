# Authentication Service Documentation - Initial Release (v1.0)

## 1. Overview

The Authentication Service for **Fidalex Bank** is a secure and modular component that handles all aspects of user identity management. This includes user registration, login, token lifecycle management, and profile access — adhering to industry standards for RESTful API design, secure cryptographic practices, and scalable PostgreSQL-backed architecture.

---

## 2. Stack & Technologies

| Layer              | Technology/Tool      | Purpose                                 |
| ------------------ | -------------------- | --------------------------------------- |
| Language           | Python 3.11+         | Backend logic                           |
| Web Framework      | FastAPI              | API development                         |
| Database           | PostgreSQL 14+       | Persistent storage                      |
| ORM                | SQLAlchemy           | Database interactions                   |
| Migrations         | Alembic              | DB version control                      |
| Password Hashing   | bcrypt               | Secure password storage                 |
| Token Management   | PyJWT                | JWT encoding/decoding                   |
| Containerization   | Docker               | Service packaging                       |
| API Gateway        | Traefik / Kong       | Secure traffic routing, TLS termination |
| Orchestration      | Kubernetes           | Microservice deployment                 |
| CI/CD              | GitHub Actions       | Continuous integration & delivery       |
| Secrets Management | dotenv / K8s Secrets | Secure configuration                    |

---

## 3. Core Responsibilities

| Area               | Functionality                                                                |
| ------------------ | ---------------------------------------------------------------------------- |
| User Lifecycle     | Register, activate, deactivate accounts                                      |
| Authentication     | Verify user identity and credentials                                         |
| Authorization      | Role-based access token generation and validation                            |
| Session Management | Refresh token lifecycle management                                           |
| Profile Access     | Endpoint for accessing own user profile (`GET /auth/me`)                     |
| Security           | Secure password hashing, JWT signature verification, rate limiting, and more |

---

## 4. API Endpoints

| Method | Endpoint       | Description                  | Auth Required | Roles |
| ------ | -------------- | ---------------------------- | ------------- | ----- |
| POST   | /auth/register | Register new user            | ❌             | -     |
| POST   | /auth/login    | Authenticate & issue JWT     | ❌             | -     |
| POST   | /auth/refresh  | Refresh expired access token | ❌             | -     |
| POST   | /auth/logout   | Revoke refresh token         | ✅             | Any   |
| GET    | /auth/me       | Fetch logged-in user profile | ✅             | Any   |

---

## 5. Database Design (PostgreSQL)

### Tables & Relationships

| Table                     | Description                                       |
| ------------------------- | ------------------------------------------------- |
| users                     | Stores registered users and account info          |
| roles                     | Stores available system roles (e.g., USER, ADMIN) |
| user\_roles               | Junction table assigning roles to users           |
| refresh\_tokens           | Stores all issued refresh tokens                  |
| password\_reset\_requests | Handles password reset requests                   |

### Schema Overview

(See original version for table DDLs)

---

## 6. Workflow Lifecycle

### 6.1. User Registration

1. User submits registration data.
2. FastAPI validates request.
3. Password hashed (bcrypt).
4. `users` row created.
5. Role "USER" assigned via `user_roles`.
6. Access + Refresh tokens generated and returned.
7. `refresh_tokens` row inserted.

### 6.2. User Login

1. User submits credentials.
2. Backend verifies user exists and password matches.
3. Tokens generated.
4. Refresh token stored.
5. Tokens returned to client.

### 6.3. Token Refresh

1. Client submits refresh token.
2. Backend checks for validity and expiration.
3. Old token marked `revoked`.
4. New tokens issued.
5. New refresh token saved.

### 6.4. Logout

1. Access token verified.
2. Submitted refresh token is marked as `revoked`.
3. Confirmation response sent.

### 6.5. Fetch Profile

1. JWT decoded to get user\_id.
2. User data and roles queried.
3. Response returned to client.

---

## 7. Response Examples

### Register - 201 Created

```json
{
  "user_id": 101,
  "access_token": "<jwt>",
  "refresh_token": "<refresh>",
  "expires_in": 3600
}
```

### Login - 401 Unauthorized

```json
{
  "detail": "Invalid credentials"
}
```

### Refresh - 401 Expired or Invalid

```json
{
  "detail": "Refresh token expired or revoked"
}
```

### Logout - 200 OK

```json
{
  "message": "Logged out successfully"
}
```

### Fetch Profile - 200 OK

```json
{
  "user_id": 101,
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "roles": ["USER"]
}
```

---

## 8. Development Lifecycle (SDLC)

| Phase        | Description                                                              |
| ------------ | ------------------------------------------------------------------------ |
| Requirements | Define auth needs (JWT, sessions, roles)                                 |
| Design       | API contract, schema design, token flow diagrams                         |
| Development  | Implement FastAPI endpoints, DB schemas                                  |
| Testing      | Unit + Integration tests for endpoints (Pytest)                          |
| Deployment   | CI/CD pipelines with Docker & Kubernetes                                 |
| Monitoring   | Enable logging, audit trails, rate limits, alerts via Prometheus/Grafana |
| Maintenance  | Bug fixes, security updates, token rotation tuning                       |

---

## 9. Environment Variables (.env)

| Variable                       | Description                   |
| ------------------------------ | ----------------------------- |
| DATABASE\_URL                  | PostgreSQL DB URI             |
| JWT\_SECRET\_KEY               | Secret key for signing JWTs   |
| ACCESS\_TOKEN\_EXPIRE\_MINUTES | JWT TTL                       |
| REFRESH\_TOKEN\_EXPIRE\_DAYS   | Refresh TTL                   |
| BCRYPT\_ROUNDS                 | Number of hashing salt rounds |

---

## 10. Security Best Practices

* All endpoints protected with HTTPS (enforced at API Gateway)
* Access tokens stored in memory / cookies (not localStorage)
* Refresh tokens stored in `refresh_tokens` table with revocation tracking
* JWTs use short expiry (15–60 mins)
* Refresh tokens are rotated and old ones revoked
* Strict validation on inputs to prevent injection/XSS

---

## 11. Release Information

| Property     | Value                        |
| ------------ | ---------------------------- |
| Version      | v1.0                         |
| Release Date | 2025-06-01                   |
| Status       | ✅ Stable                     |
| Owner        | Ashur raju addanki           |
| Maintainers  | Ashur raju Addanki |
| Environments | Dev, Test, Prod              |

---

## 12. Future Enhancements

* Email verification workflow
* Password reset via OTP/email links
* Device-based session tracking
* Multi-factor authentication (MFA)
* Admin dashboard for account management
* OpenID Connect or OAuth2 federation support

---

## 13. Appendix

* Postman Collection: \[Pending Upload]
* ERD Diagram: \[Available in DB Repo]
* Swagger UI: `https://api.fidalexbank.com/docs`
* Kubernetes Helm Chart: \[In Infra Repo]
Ashur Raju Addanki