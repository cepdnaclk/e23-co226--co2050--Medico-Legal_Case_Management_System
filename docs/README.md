---
layout: home
permalink: index.html

# Please update this with your repository name and title
repository-name: e23-co2050-Medico-Legal Case Management System
title: Medico-Legal Case Management System
---

# Medico-Legal Case Management System

---

## Team
-  E23076, M.T. Dineth, [e23076@eng.pdn.ac.lk](mailto:e23076@eng.pdn.ac.lk)
-  E23122, P.H.S. Gunawardhana, [e23122@eng.pdn.ac.lk](mailto:e23122@eng.pdn.ac.lk)
-  E23050, G.C. Damsiluni, [e23050@eng.pdn.ac.lk](mailto:e23050@eng.pdn.ac.lk)
-  E23089, M.A.S. Dulashara, [e23089@eng.pdn.ac.lk](mailto:e23089@eng.pdn.ac.lk)

## Table of Contents
1. [Introduction](#introduction)
    - [The Real-World Problem](#the-real-world-problem)
    - [The Solution](#the-solution)
    - [The Impact](#the-impact)
2. [System Architecture & Features](#system-architecture--features)
    - [1. Unified Technology Stack](#1-unified-technology-stack)
    - [2. Normalized 25-Table Schema Matrix](#2-normalized-25-table-schema-matrix)
    - [3. Defensive Security Implementations](#3-defensive-security-implementations)
3. [Links](#links)

---

## Introduction

### The Real-World Problem
Forensic Medical Departments traditionally rely heavily on manual, paper-based record-keeping workflows. This localized data management introduces severe structural and legal vulnerabilities:
* **Confidentiality Tiers:** Physical storage lacks access tracking, exposing highly sensitive patient Personally Identifiable Information (PII) and judicial autopsy findings to unauthorized internal or external eyes.
* **Data Deterioration & Loss:** Physical paper files degrade organically over time and face constant risks of physical destruction, misplacement, or un-audited tampering.
* **Chain of Custody Vulnerabilities:** Documenting the hand-off, storage, and processing of critical forensic laboratory evidence manually is prone to human oversight, endangering the legal admissibility of evidence in a court of law.
* **Administrative Latency:** Compiling medical details manually drastically slows down the generation of final legal court reports, leading to prolonged delays in judicial proceedings.

### The Solution
The **Medico-Legal Case Management System** is a secure, cloud-native relational platform engineered to completely digitize, streamline, and safeguard forensic operations. Developed with a high-performance **Python Flask** backend and backed by an enterprise-grade **Supabase PostgreSQL** cloud database, the architecture transforms manual records into an immutable digital workspace. The core system relies on a 25-table schema designed strictly under the 3rd Normal Form (3NF) to guarantee absolute data consistency and referential integrity.

### The Impact
By transitioning to this digitized framework, the Forensic Department achieves:
* **Hardened Data Security:** Comprehensive cryptographic protection of administrative credentials and structured encryption of sensitive fields.
* **Uncompromising Legal Accountability:** The execution of database-level tracking hooks ensures that every case modification and evidence hand-off leaves a permanent, transparent paper trail suitable for rigorous court verification.
* **Operational Acceleration:** Eliminating physical searches allows the system to instantaneously compile data, accelerating the turnaround time for official medical and court reports.
* **Regulatory Compliance:** Built in total alignment with modern data security standards and regional privacy protocols, such as the Sri Lanka Personal Data Protection Act No. 9 of 2022.

---

## System Architecture & Features

### 1. Unified Technology Stack
The platform leverages clean, efficient, and decoupled technologies optimized for security, transparency, and rapid deployment:
* **Backend Framework:** Python Flask (Handling core business logic, query parameterization, and session management)
* **Database Infrastructure:** PostgreSQL via Supabase Cloud (Providing relational data storage, transactional rollbacks, and multi-tenant scaling)
* **Security & Cryptography:** Werkzeug Security Engine (Managing irreversible cryptographic primitives and access-control validations)
* **User Interface:** Clean, highly responsive frontend developed using Vanilla HTML5, CSS3, and asynchronous modern JavaScript.

### 2. Normalized 25-Table Schema Matrix
To enforce strict data isolation and eliminate redundancy, the relational database structure is partitioned into six highly integrated system modules:
* **Core Access & Identity:** Tracks system roles, granular permissions, and cryptographic user profiles (`users`, `staff`, `role`, `role_permissions`).
* **Patient Demographics:** Secures patient identification data, clinical histories, and contact records (`patient`, `patient_medical_history`, `next_of_kin`, `patient_contact`).
* **Case Management:** Coordinates core legal incidents, mapping them to types, statuses, and reporting police stations (`medicolegalcase`, `casetype`, `casestatus`, `policestation`, `incident_location`).
* **Autopsy & Mortuary Operations:** Details physical postmortem examinations, precise organ weight registries, and body storage assignments (`postmortem`, `organ_examination`, `body_storage`, `disposal_record`).
* **Evidence & Laboratory Tracking:** Structural enforcement of forensic element ingestion, sample tracking, and parameter testing (`evidence`, `chain_of_custody`, `laboratory_test`, `test_parameter`, `test_result`).
* **Legal Reporting & Auditing:** Compiles formal external submissions and houses the automated security ledger (`court_report`, `medical_report`, `auditlog`).

### 3. Defensive Security Implementations
Security was woven directly into the code and database engine layers rather than being treated as an afterthought:
* **Cryptographic Hashing:** User passwords are transformed using non-reversible `pbkdf2:sha256` hashing algorithms paired with randomized salts prior to database storage, insulating the system from credential harvesting.
* **Role-Based Access Control (RBAC):** Custom Python route decorators (`@login_required` and `@role_required`) operate as middleware bouncers, validating signed session badges on every HTTP request and redirecting unprivileged entities.
* **Database-Level Audit Triggers:** An automated `AFTER INSERT` trigger is written natively into the PostgreSQL layer. The millisecond a case is created, the engine bypasses the application layer to write an immutable record into the `auditlog`, tracking the user, action, and explicit timestamp.
* **Data Isolation (IDOR Defenses):** All read/write SQL interactions are explicitly parameterized and bound to the logged-in user's session identifier (`WHERE assigneddoctor = session['userid']`), blocking malicious IDOR url manipulations and securing patient privacy.

---

## Links

- [Project Repository](https://github.com/cepdnaclk/e23-co226--co2050--Medico-Legal_Case_Management_System)
- [Project Page](https://cepdnaclk.github.io/e23-co226--co2050--Medico-Legal_Case_Management_System)
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)
