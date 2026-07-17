# Forensic Medical Department Database System
**Department of Computer Engineering, University of Peradeniya**
*Mini Project Assignment: Database Systems*

This repository contains the source code and database schema for a fully functional Forensic Medical Department Database System. It is built using a lightweight **Python Flask** backend, a **MySQL** relational database, and vanilla **HTML/CSS/JavaScript** for the frontend to ensure maximum performance and clean integration.

## 👥 Team Structure
Based on the project requirements, our team of four is organized as follows:

* **P.H.S. Gunawardhana** – Project Coordinator / Team Leader (Coordination, Submission, Final Compiled Report)
* **G.C. Damsiluni** – System Analyst / Requirement Analyst (SRS, Workflow Descriptions, Requirement Gathering)
* **M.A.S. Dulashara** – Database Designer & QA (ER Diagrams, Relational Schema, Normalization, Testing)
* **M.T. Dineth** – Web/Application Developer (UI Development, SQL Implementation, Interface Linking)

---

## 🛠️ Tech Stack
* **Backend:** Python 3.x, Flask
* **Database:** MySQL Server (`mysql-connector-python`)
* **Frontend:** HTML5, CSS3 (Vanilla, No external frameworks)

---

## 🚀 How to Run the Project Locally 

To run this project on your own machine for testing and development, follow these steps exactly:

### Step 1: Install Prerequisites
Ensure you have the following installed on your computer:
1.  **Python 3.x:** (Check by running `python --version` in your terminal).
2.  **MySQL Server:** (XAMPP, WAMP, or MySQL Workbench).

### Step 2: Set up the Database
1.  Open your MySQL environment (e.g., phpMyAdmin or MySQL Workbench).
2.  Locate the `database_schema.sql` file provided in this repository.
3.  Execute the entire script to create the `forensic_db` database, build all normalized tables (Staff, Users, Patient, MedicoLegalCase, Postmortem, Evidence, LaboratoryTest, CourtReport), and insert the mock testing data.

### Step 3: Install Python Dependencies
Open your terminal or command prompt, navigate to the project folder, and install Flask and the MySQL connector:
`pip install Flask mysql-connector-python`

### Step 4: Configure Database Credentials
Open `app.py` in your code editor. Near the top of the file, find the `db_config` dictionary. **You must update the password to match your local MySQL root password.**

```python
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_LOCAL_MYSQL_PASSWORD', # Update this!
    'database': 'forensic_db'
}

Step 5: 

Start the ServerIn your terminal, ensure you are in the project folder and run:python app.pyIf successful, the terminal will show that the server is running on http://127.0.0.1:5000. Open this URL in your web browser.

🔐 Mock Test CredentialsTo test the role-based access control and session management, use the following mock accounts that were injected into the database during setup:

RoleUsernamePasswordAccess LevelDoctor / JMOkamal_jmohashed_pw_1Case Management, Postmortem, Court ReportsLaboratory Staffsaman_labhashed_pw_2Evidence Management, Lab TestsClerical Officerruwanthi_clerkhashed_pw_3Patient Registration

📂 Project Directory StructurePlaintext/forensic-database-system
│
├── app.py                      # Main backend application logic and routing
├── database_schema.sql         # SQL script to initialize tables and sample data
├── README.md                   # Project documentation and setup guide
│
└── templates/                  # Frontend HTML files
    ├── login.html              # Secure authentication interface
    ├── dashboard.html          # Role-based main navigation and statistics
    ├── register_patient.html   # Form to add new patient profiles
    ├── create_case.html        # Form to open Medico-Legal cases
    ├── view_cases.html         # Searchable case directory table
    ├── postmortem.html         # Form to log autopsy findings
    ├── manage_evidence.html    # Chain of custody tracking form
    ├── lab_test.html           # Form to log laboratory analysis results
    └── court_report.html       # Medico-legal report generation tracking

