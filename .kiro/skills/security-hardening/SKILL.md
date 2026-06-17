---
name: security-hardening
description: Provides guidelines for securing general web applications, protecting against vulnerability vectors, and establishing access control boundaries.
---

# Security and Hardening

## Overview

Security must be built into a web application from the start, not added as an afterthought. This skill outlines standard practices to protect client-server architectures against common security vulnerabilities (e.g., OWASP Top 10) and ensure robust access control.

---

## 1. Authentication & Session Management

- **Storage**: Never store raw JWT tokens in browser `localStorage` or `sessionStorage` if they contain sensitive permissions, as they are vulnerable to XSS. Prefer `HttpOnly`, `Secure`, `SameSite=Lax/Strict` cookies.
- **Token Handling**: Use short-lived Access Tokens and long-lived, rotating Refresh Tokens. Refresh tokens must be stored securely and revoked if reuse is detected.
- **Passwords**: Always hash passwords on the backend before storing them in the database using strong, modern algorithms (e.g., Argon2id or bcrypt). Never store passwords in plain text.
- **OAuth/OIDC**: When implementing OAuth (e.g., Login with Google/GitHub), implement State parameters and PKCE (Proof Key for Code Exchange) to prevent authorization code interception attacks.

---

## 2. Authorization & Data Access Control

- **Server-Side Verification**: Never trust the frontend client to dictate permissions. Always check authorizations on the backend server for every request.
- **Access Control Models**:
  - **RBAC (Role-Based Access Control)**: Assign permissions to roles (e.g., `admin`, `editor`, `viewer`) and roles to users.
  - **ABAC/Row-Level Security (RLS)**: Enforce context-aware permissions (e.g., a user can only edit or view posts where `user_id == current_user.id`).
- **Default Deny**: APIs should default to denying access. Explicitly allow access only for authenticated and authorized requests.

---

## 3. Input Validation & Output Sanitization

- **Client vs. Server**: Frontend validation is for User Experience (UX); backend validation is for Security. *Never bypass backend validation.*
- **Schema Validation**: Parse and validate all incoming request parameters, headers, query params, and body JSON payloads using schema validation libraries (e.g., Zod, Yup, Joi, Pydantic).
- **SQL Injection (SQLi)**: Never concatenate strings to build SQL queries. Always use parameterized queries, prepared statements, or ORM frameworks (e.g., Prisma, Hibernate, SQLAlchemy).
- **XSS (Cross-Site Scripting)**: Sanitize and encode any user-supplied content before rendering it in the browser. Use framework-native sanitization (e.g., React's automatic encoding, or DOMPurify for HTML content).

---

## 4. Secure Network Headers & CORS

- **CORS (Cross-Origin Resource Sharing)**: Configure CORS origins strictly. Avoid using wildcard `Access-Control-Allow-Origin: *` in production unless it's a public API. Specify explicit domains (e.g., `https://app.example.com`).
- **Content Security Policy (CSP)**: Configure CSP headers to restrict the sources from which scripts, styles, images, and other assets can be loaded, reducing XSS risks.
- **HSTS (HTTP Strict Transport Security)**: Enforce HTTPS for all browser-to-server communications using HSTS headers.
- **Other Security Headers**:
  - `X-Frame-Options: DENY` or `SAMEORIGIN` (prevents clickjacking).
  - `X-Content-Type-Options: nosniff` (prevents MIME type sniffing).
  - `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 5. Secrets Management

- **Environment Separation**: Use `.env` or configuration vaults to store secret tokens, database credentials, and private API keys.
- **Repository Safety**: Add `.env` to `.gitignore`. Never commit credentials to git.
- **Leak Recovery**: If a secret is committed to git, immediately rotate it, revoke the old key, and clean git history using tools like `git-filter-repo` or `BFG Repo-Cleaner`.
