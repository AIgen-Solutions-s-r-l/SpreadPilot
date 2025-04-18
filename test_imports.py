import importlib

# Test importing from hyphenated directories
print("Testing imports from hyphenated directories...")

# Trading bot
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
print("✅ Successfully imported trading-bot.app.service.signals")

# Admin API
admin_api_main = importlib.import_module('admin-api.app.main')
print("✅ Successfully imported admin-api.app.main")

# Alert router
alert_router_service = importlib.import_module('alert-router.app.service.router')
print("✅ Successfully imported alert-router.app.service.router")

# Report worker
report_worker_service = importlib.import_module('report-worker.app.service.pnl')
print("✅ Successfully imported report-worker.app.service.pnl")

print("All imports successful!")