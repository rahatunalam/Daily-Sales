from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('customers', views.CustomerViewSet, basename='customer')
router.register('transactions', views.TransactionViewSet, basename='transaction')
router.register('mfs-accounts', views.MfsViewSet, basename='mfs')
router.register('denominations', views.DenominationViewSet, basename='denomination')
router.register('companies', views.CompanyViewSet, basename='company')
router.register('company-entries', views.CompanyEntryViewSet, basename='company-entry')

page_urls = [
    path('', views.index, name='index'),
    path('login/', views.login_page, name='login'),
    path('daily-sales/', views.daily_sales_page, name='daily_sales'),
    path('due/', views.due_page, name='due'),
    path('whole-sale/', views.whole_sale_page, name='whole_sale'),
    path('company-payment/', views.company_payment_page, name='company_payment'),
    path('day-closing/', views.day_closing_page, name='day_closing'),
    path('report/', views.report_page, name='report'),
    path('settings/', views.settings_page, name='settings'),
]

api_urls = [
    path('auth/login/', views.login),
    path('auth/logout/', views.logout),
    path('auth/me/', views.me),
    path('auth/change-password/', views.change_password),
    path('opening-balance/', views.opening_balance),
    path('daily-summary/', views.daily_summary),
    path('day-closing/', views.day_closing),
    path('reports/daily/', views.daily_report),
    path('reports/daily/details/', views.daily_report_details),
] + router.urls

urlpatterns = page_urls + [path('api/', include(api_urls))]