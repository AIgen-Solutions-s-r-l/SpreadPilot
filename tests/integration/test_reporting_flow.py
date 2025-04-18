"""Integration tests for the reporting flow."""

import asyncio
import datetime
import decimal
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from spreadpilot_core.models.follower import Follower
from spreadpilot_core.models.position import Position
from spreadpilot_core.models.trade import Trade, TradeSide, TradeStatus

import importlib

# Import modules using importlib
report_worker_pnl = importlib.import_module('report-worker.app.service.pnl')

# Get specific imports
calculate_daily_pnl = report_worker_pnl.calculate_daily_pnl
calculate_monthly_pnl = report_worker_pnl.calculate_monthly_pnl
calculate_commission = report_worker_pnl.calculate_commission

# Import more modules using importlib
report_worker_generator = importlib.import_module('report-worker.app.service.generator')
report_worker_notifier = importlib.import_module('report-worker.app.service.notifier')

# Get specific imports
generate_monthly_report = report_worker_generator.generate_monthly_report
send_monthly_report = report_worker_notifier.send_monthly_report


@pytest.mark.asyncio
async def test_daily_pnl_calculation(
    firestore_client,
    test_follower,
):
    """
    Test the daily P&L calculation process.
    
    This test verifies:
    1. Closed positions are fetched from Firestore
    2. P&L is calculated correctly
    3. Results are stored in Firestore
    """
    # Create test closed positions for today
    today = datetime.date.today()
    
    # Create a few closed trades with known P&L
    trades = []
    total_pnl = Decimal("0.0")
    
    for i in range(3):
        pnl = Decimal(str(100.0 + i * 50.0))  # 100, 150, 200
        total_pnl += pnl
        
        trade = {
            "followerId": test_follower.id,
            "side": TradeSide.LONG.value if i % 2 == 0 else TradeSide.SHORT.value,
            "qty": 1,
            "strike": 380.0 + i * 5.0,
            "limitPriceRequested": 0.75,
            "status": TradeStatus.FILLED.value,
            "pnl": str(pnl),  # Store as string for precision
            "closeTimestamp": datetime.datetime.combine(today, datetime.time(12, 0)),
            "timestamps": {
                "submitted": datetime.datetime.combine(today, datetime.time(9, 30)),
                "filled": datetime.datetime.combine(today, datetime.time(9, 31)),
            },
            "createdAt": datetime.datetime.combine(today, datetime.time(9, 0)),
            "updatedAt": datetime.datetime.combine(today, datetime.time(12, 1)),
        }
        
        trade_id = f"test-trade-{uuid.uuid4()}"
        firestore_client.collection("trades").document(trade_id).set(trade)
        trades.append((trade_id, trade))
    
    # Calculate daily P&L
    with patch("report_worker.app.service.pnl.db", firestore_client):
        result = calculate_daily_pnl(today)
    
    # Verify result
    assert result == total_pnl
    
    # Verify P&L was stored in Firestore
    daily_pnl_doc = firestore_client.collection("daily_pnl").document(today.isoformat()).get()
    assert daily_pnl_doc.exists
    
    daily_pnl_data = daily_pnl_doc.to_dict()
    assert daily_pnl_data["date"] == today.isoformat()
    assert Decimal(daily_pnl_data["total_pnl"]) == total_pnl
    assert daily_pnl_data["positions_processed"] == len(trades)
    
    # Clean up
    for trade_id, _ in trades:
        firestore_client.collection("trades").document(trade_id).delete()


@pytest.mark.asyncio
async def test_monthly_pnl_calculation(
    firestore_client,
):
    """
    Test the monthly P&L calculation process.
    
    This test verifies:
    1. Daily P&L records are aggregated for the month
    2. Monthly total is calculated correctly
    """
    # Create test daily P&L records for the current month
    today = datetime.date.today()
    year = today.year
    month = today.month
    
    # Create daily P&L records with known values
    daily_pnls = []
    total_monthly_pnl = Decimal("0.0")
    
    # Create records for 5 days in the current month
    for day in range(1, 6):
        try:
            date = datetime.date(year, month, day)
        except ValueError:
            # Skip invalid dates
            continue
        
        daily_pnl = Decimal(str(100.0 * day))  # 100, 200, 300, 400, 500
        total_monthly_pnl += daily_pnl
        
        daily_pnl_data = {
            "date": date.isoformat(),
            "total_pnl": str(daily_pnl),
            "calculation_timestamp": datetime.datetime.now(),
            "positions_processed": day,
        }
        
        firestore_client.collection("daily_pnl").document(date.isoformat()).set(daily_pnl_data)
        daily_pnls.append((date.isoformat(), daily_pnl_data))
    
    # Calculate monthly P&L
    with patch("report_worker.app.service.pnl.db", firestore_client):
        result = calculate_monthly_pnl(year, month)
    
    # Verify result
    assert result == total_monthly_pnl
    
    # Clean up
    for doc_id, _ in daily_pnls:
        firestore_client.collection("daily_pnl").document(doc_id).delete()


@pytest.mark.asyncio
async def test_commission_calculation(
    test_follower,
):
    """
    Test the commission calculation based on monthly P&L.
    
    This test verifies:
    1. Commission is calculated correctly based on follower's commission percentage
    2. Zero commission for negative P&L
    """
    # Test with positive P&L
    monthly_pnl = Decimal("1000.00")
    expected_commission = monthly_pnl * (Decimal(str(test_follower.commission_pct)) / Decimal("100.0"))
    
    result = calculate_commission(monthly_pnl, test_follower)
    assert result == expected_commission
    
    # Test with negative P&L (should return zero commission)
    negative_pnl = Decimal("-500.00")
    result = calculate_commission(negative_pnl, test_follower)
    assert result == Decimal("0.0")
    
    # Test with zero P&L
    zero_pnl = Decimal("0.0")
    result = calculate_commission(zero_pnl, test_follower)
    assert result == Decimal("0.0")


@pytest.mark.asyncio
async def test_monthly_report_generation(
    firestore_client,
    test_follower,
    mock_ibkr_client,
):
    """
    Test the generation of monthly reports.
    
    This test verifies:
    1. Monthly P&L is calculated
    2. Report is generated with correct data
    3. Report is stored in Firestore
    """
    # Setup test data
    today = datetime.date.today()
    year = today.year
    month = today.month
    
    # Create daily P&L records
    total_monthly_pnl = Decimal("1500.00")
    daily_pnl_data = {
        "date": today.replace(day=15).isoformat(),  # Middle of month
        "total_pnl": str(total_monthly_pnl),
        "calculation_timestamp": datetime.datetime.now(),
        "positions_processed": 10,
    }
    firestore_client.collection("daily_pnl").document(today.replace(day=15).isoformat()).set(daily_pnl_data)
    
    # Mock the calculate_monthly_pnl function
    with patch("report_worker.app.service.generator.calculate_monthly_pnl", return_value=total_monthly_pnl):
        # Mock the calculate_commission function
        expected_commission = total_monthly_pnl * (Decimal(str(test_follower.commission_pct)) / Decimal("100.0"))
        with patch("report_worker.app.service.generator.calculate_commission", return_value=expected_commission):
            # Generate monthly report
            report = await generate_monthly_report(
                year=year,
                month=month,
                follower=test_follower,
                db=firestore_client,
            )
    
    # Verify report data
    assert report["follower_id"] == test_follower.id
    assert report["year"] == year
    assert report["month"] == month
    assert Decimal(report["total_pnl"]) == total_monthly_pnl
    assert Decimal(report["commission_amount"]) == expected_commission
    assert "report_id" in report
    
    # Verify report was stored in Firestore
    report_doc = firestore_client.collection("monthly_reports").document(report["report_id"]).get()
    assert report_doc.exists
    
    report_data = report_doc.to_dict()
    assert report_data["followerId"] == test_follower.id
    assert report_data["year"] == year
    assert report_data["month"] == month
    assert Decimal(report_data["totalPnl"]) == total_monthly_pnl
    assert Decimal(report_data["commissionAmount"]) == expected_commission
    
    # Clean up
    firestore_client.collection("daily_pnl").document(today.replace(day=15).isoformat()).delete()
    firestore_client.collection("monthly_reports").document(report["report_id"]).delete()


@pytest.mark.asyncio
async def test_monthly_report_email_sending(
    mock_email_sender,
    test_follower,
):
    """
    Test sending monthly reports via email.
    
    This test verifies:
    1. Email is sent to the follower
    2. Email contains correct report data
    3. PDF attachment is included
    """
    # Create test report data
    report = {
        "report_id": f"report-{uuid.uuid4()}",
        "follower_id": test_follower.id,
        "year": datetime.date.today().year,
        "month": datetime.date.today().month,
        "total_pnl": "1500.00",
        "commission_amount": "300.00",
        "net_pnl": "1200.00",
        "generated_at": datetime.datetime.now().isoformat(),
    }
    
    # Mock PDF generation
    with patch("report_worker.app.service.notifier.generate_pdf_report", return_value=b"mock-pdf-content"):
        # Send report
        result = await send_monthly_report(report, test_follower)
    
    # Verify email was sent
    assert result is True
    mock_email_sender.assert_called_once()
    
    # Verify email content
    email_args = mock_email_sender.call_args[1]
    assert test_follower.email in email_args["recipients"]
    assert f"Monthly Report: {report['month']}/{report['year']}" in email_args["subject"]
    assert report["total_pnl"] in email_args["body"]
    assert report["commission_amount"] in email_args["body"]
    assert "attachments" in email_args
    assert len(email_args["attachments"]) == 1
    assert email_args["attachments"][0][0].endswith(".pdf")


@pytest.mark.asyncio
async def test_end_to_end_reporting_flow(
    firestore_client,
    test_follower,
    mock_email_sender,
    mock_ibkr_client,
):
    """
    Test the end-to-end reporting flow.
    
    This test verifies:
    1. Daily P&L is calculated
    2. Monthly P&L is aggregated
    3. Report is generated
    4. Email is sent
    """
    # Setup test data
    today = datetime.date.today()
    year = today.year
    month = today.month
    
    # Create daily P&L records
    total_monthly_pnl = Decimal("2000.00")
    daily_pnl_data = {
        "date": today.replace(day=15).isoformat(),  # Middle of month
        "total_pnl": str(total_monthly_pnl),
        "calculation_timestamp": datetime.datetime.now(),
        "positions_processed": 10,
    }
    firestore_client.collection("daily_pnl").document(today.replace(day=15).isoformat()).set(daily_pnl_data)
    
    # Mock functions to isolate the flow
    with patch("report_worker.app.service.pnl.db", firestore_client):
        with patch("report_worker.app.service.pnl.calculate_daily_pnl", return_value=total_monthly_pnl):
            with patch("report_worker.app.service.generator.generate_pdf_report", return_value=b"mock-pdf-content"):
                # Run the end-to-end flow
                report_worker_report_service = importlib.import_module('report-worker.app.service.report_service')
                generate_and_send_monthly_reports = report_worker_report_service.generate_and_send_monthly_reports
                
                # Mock get_all_active_followers
                with patch("report_worker.app.service.report_service.get_all_active_followers", return_value=[test_follower]):
                    result = await generate_and_send_monthly_reports(year, month)
    
    # Verify results
    assert result["success"] is True
    assert len(result["reports"]) == 1
    assert result["reports"][0]["follower_id"] == test_follower.id
    assert Decimal(result["reports"][0]["total_pnl"]) == total_monthly_pnl
    
    # Verify email was sent
    mock_email_sender.assert_called_once()
    
    # Clean up
    firestore_client.collection("daily_pnl").document(today.replace(day=15).isoformat()).delete()
    if "report_id" in result["reports"][0]:
        firestore_client.collection("monthly_reports").document(result["reports"][0]["report_id"]).delete()