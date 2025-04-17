# Task: Implement Report Worker Service (TASK-REPORT-WORKER-IMPL)

**Goal:** Implement the `report-worker` service responsible for calculating P&L, generating monthly PDF/Excel reports, and emailing them to followers, based on the provided requirements. The service should leverage `spreadpilot-core` and follow the project's established modular structure.

**Design Plan:**

1.  **Structure:** Create `app/config.py`, `app/main.py`, `app/service/pnl.py`, `app/service/generator.py`, `app/service/notifier.py`, `app/service/report_service.py`.
2.  **Dependencies:** Define `requirements.in` (Done).
3.  **Configuration:** Implement `config.py` for settings (commission %, emails, GCP project ID).
4.  **P&L Logic:** Implement `pnl.py` to fetch Firestore `Position` data, calculate daily/monthly P&L, and commissions.
5.  **Report Generation:** Implement `generator.py` using `spreadpilot_core` utils for PDF/Excel.
6.  **Notification:** Implement `notifier.py` using `spreadpilot_core` utils for email.
7.  **Orchestration:** Implement `report_service.py` to coordinate the process for each follower.
8.  **Entry Point:** Implement `main.py` with Flask to handle Pub/Sub triggers.
9.  **Deployment:** Create `Dockerfile`.
10. **Logging:** Integrate `spreadpilot_core.logging` throughout.


**Status:** ✅ Complete

**Outcome:** Success

**Summary:**
Implemented the `report-worker` service as a standalone Flask application designed for Cloud Run. The service handles Pub/Sub triggers for two job types:
1.  **`daily`**: Calculates and stores the total P&L for closed positions on the trigger date using `pnl.calculate_and_store_daily_pnl`.
2.  **`monthly` (default)**: Calculates the total P&L for the *previous* month by aggregating daily P&L data (`pnl.calculate_monthly_pnl`), fetches active followers (`report_service._get_active_followers`), calculates commission per follower (`pnl.calculate_commission`), generates PDF and Excel reports (`generator.generate_pdf_report`, `generator.generate_excel_report`), and emails them to the follower with admin CC'd (`notifier.send_report_email`).

The implementation leverages the `spreadpilot-core` library for logging, Firestore models, and utility functions (PDF, Excel, Email). Configuration is loaded from environment variables via `config.py`. The service structure follows the modular pattern established in other project services.
A `Dockerfile` is provided for containerization.

**Testing:** Unit/integration tests were not explicitly requested but should be added (potentially delegated to `test-developer`) to ensure robustness before deployment.

**File References:**
*   `report-worker/app/config.py` (created)
*   `report-worker/app/main.py` (created)
*   `report-worker/app/service/__init__.py` (created)
*   `report-worker/app/service/pnl.py` (created)
*   `report-worker/app/service/generator.py` (created)
*   `report-worker/app/service/notifier.py` (created)
*   `report-worker/app/service/report_service.py` (created)
*   `report-worker/requirements.in` (created)
*   `report-worker/Dockerfile` (created)
*   `project_journal/tasks/TASK-REPORT-WORKER-IMPL.md` (updated)