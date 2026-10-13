# FLODSS Installation & Deployment Guide: Local-First Setup
## Facility Layout Optimization & Decision Support System (`v1.0.0-rc.1`)

This guide provides instructions for installing and running FLODSS on a local workstation or dedicated research computer running Windows, Linux, or macOS.

---

## 1. System Requirements

### Hardware Requirements
- **CPU:** Dual-core 2.0 GHz or higher (Quad-core recommended for large population Genetic Algorithm runs).
- **RAM:** Minimum 4 GB (8 GB recommended for 15+ department problems with large Pareto candidate portfolios).
- **Disk Space:** 500 MB free space for code, dependencies, and experiment logs.

### Software Prerequisites
- **Python:** Version 3.12 or newer. Verify with:
  ```bash
  python --version
  ```
- **Node.js:** Version 18.x or 20.x LTS. Verify with:
  ```bash
  node --version
  npm --version
  ```

---

## 2. Installation Steps

### Step 1: Clone or Unpack the Repository
Ensure all files are placed in a dedicated local directory (e.g., `C:\Facility` or `~/Facility`).

```bash
cd Facility
```

---

### Step 2: Backend Setup (Python 3.12+)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   - **Windows:**
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Upgrade `pip` and install package dependencies in editable mode:
   ```bash
   python -m pip install --upgrade pip setuptools wheel
   pip install -e .
   ```

4. Verify backend test suite (377 tests):
   ```bash
   pytest -q
   ```
   *Expected output:* `377 passed, 1 warning in ~20s`.

---

### Step 3: Frontend Setup (React 18 & TypeScript)

1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd Facility/frontend
   ```

2. Install npm packages:
   ```bash
   npm install
   ```

3. Verify TypeScript build:
   ```bash
   npm run build
   ```
   *Expected output:* `✓ built in ...` with zero errors.

---

## 3. Configuration & Environment Variables

FLODSS operates with secure, local-first defaults. Configuration is managed in `backend/app/core/config.py` and can be overridden via `.env` or system environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `"Facility Layout Optimization & Decision Support System"` | Platform application title |
| `VERSION` | `"1.0.0-rc.1"` | Release candidate version string |
| `API_V1_PREFIX` | `"/api"` | Backend REST API prefix |
| `DEBUG` | `false` | Enable verbose FastAPI debug logs |
| `AI_ENABLED` | `false` | Cloud Gemini AI toggle (Strictly `false` by default for confidentiality) |
| `GEMINI_API_KEY`| `None` | Optional Google AI Studio API key |
| `GEMINI_MODEL` | `"gemini-3.8-flash"` | Gemini model used if external AI is consented |
| `GEMINI_TIMEOUT_SECONDS` | `15.0` | Timeout threshold for AI responses |

> [!IMPORTANT]
> **Data Confidentiality Notice:** Leave `AI_ENABLED=false` to ensure 100% offline execution. The platform's `LocalDeterministicExplainer` operates completely within local memory with zero external data transmission.

---

## 4. Running the Application

### 1. Launch FastAPI Backend
In your backend terminal (with `.venv` activated):
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Endpoint: `http://127.0.0.1:8000`
- Swagger Documentation: `http://127.0.0.1:8000/docs`
- Health Diagnostic: `http://127.0.0.1:8000/api/health`

### 2. Launch React Frontend
In your frontend terminal:
```bash
npm run dev
```
- Web Application Interface: `http://localhost:5173`

Open your web browser and navigate to `http://localhost:5173` to access the FLODSS Engineering Workspace.

---

## 5. Troubleshooting & FAQ

### Issue: `python : The term 'python' is not recognized`
- Ensure Python 3.12 is added to your system `PATH`.
- On Windows, verify with `py -3.12 --version` or use the full path to `python.exe`.

### Issue: Port 8000 or 5173 Already in Use
- To run the backend on a different port:
  ```bash
  uvicorn app.main:app --host 127.0.0.1 --port 8080
  ```
- If you change the backend port, update Vite's proxy configuration in `frontend/vite.config.ts`.

### Issue: Frontend Displays "Backend Offline"
- Check that the backend uvicorn server is running on `http://127.0.0.1:8000`.
- Verify that `http://127.0.0.1:8000/api/health` returns status `200 OK`.
