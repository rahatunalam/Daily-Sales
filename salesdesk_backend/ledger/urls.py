from django.urls import path

from .views import DailyReportView, ReportDetailView, DailySummaryView, DayClosingView, OpeningBalanceView

urlpatterns = [
    path("daily-summary/", DailySummaryView.as_view(), name="daily-summary"),
    path("opening-balance/", OpeningBalanceView.as_view(), name="opening-balance"),
    path("day-closing/", DayClosingView.as_view(), name="day-closing"),
    path("reports/daily/", DailyReportView.as_view(), name="report-daily"),
    path("reports/daily/details/", ReportDetailView.as_view(), name="report-daily-details"),
]
