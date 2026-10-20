from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, TransactionViewSet

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("customers", CustomerViewSet, basename="customer")
urlpatterns = router.urls
