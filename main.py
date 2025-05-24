from app import app
import routes  # noqa: F401
import auth  # noqa: F401
from scheduler import start_scheduler

if __name__ == "__main__":
    # Start the background scheduler for CSV imports
    start_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=True)
