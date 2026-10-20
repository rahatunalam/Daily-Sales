from rest_framework.routers import DefaultRouter

from .views import DenominationViewSet, MfsAccountViewSet

router = DefaultRouter()
router.register("mfs-accounts", MfsAccountViewSet, basename="mfs-account")
router.register("denominations", DenominationViewSet, basename="denomination")
urlpatterns = router.urls
