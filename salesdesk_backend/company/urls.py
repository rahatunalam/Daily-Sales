from rest_framework.routers import DefaultRouter

from .views import CompanyEntryViewSet, CompanyViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("company-entries", CompanyEntryViewSet, basename="company-entry")
urlpatterns = router.urls
