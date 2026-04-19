## Deployment Documentation (Railway)

This API is deployed on [Railway.app](https://railway.app/), providing a fast, scalable, and secure cloud environment.

### Accessing the Deployment
* **Base URL:** `https://acme-logistics-api-production.up.railway.app`
* **Interactive API Docs (Swagger UI):** `https://acme-logistics-api-production.up.railway.app/docs`
*(Note: All sensitive endpoints require the `X-API-Key` or `Bearer Token` header for access).*

### 🛠️ How to Reproduce the Deployment
To deploy your own instance of this architecture, follow these steps:

1. **Repository Setup:**
   * Clone this repository to your local machine.
   * Ensure `requirements.txt` includes: `fastapi`, `uvicorn`, `fpdf2`, `requests`, `python-multipart`.
   * Push the repository to your own GitHub account.

2. **Railway Configuration:**
   * Create an account on [Railway.app](https://railway.app/).
   * Click **"New Project"** -> **"Deploy from GitHub repo"** and select your repository.
   * Railway will automatically detect the Python/FastAPI environment.

3. **Environment Variables:**
   * Go to the "Variables" tab in your Railway project.
   * Add the following secure variables:
     * `MY_API_KEY` = `[Your-Secure-String-Here]` (Used by HappyRobot to authenticate).
     * `FMCSA_KEY` = `[Your-DOT-API-Key]` (Optional, for real-time carrier verification).

4. **Launch:**
   * Railway will automatically build and deploy. Once the build is green, your API is live and generating an ephemeral `load_board` in memory.
