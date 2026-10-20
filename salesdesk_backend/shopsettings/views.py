from rest_framework import mixins, viewsets

from accounts.permissions import OwnerWriteAnyoneRead

from .models import Denomination, MfsAccount
from .serializers import DenominationSerializer, MfsAccountSerializer


class MfsAccountViewSet(viewsets.ModelViewSet):
    """Settings > Add MFS. Everyone reads (wallet choice in Daily Sales); owner edits."""

    queryset = MfsAccount.objects.all()
    serializer_class = MfsAccountSerializer
    permission_classes = [OwnerWriteAnyoneRead]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options"]


class DenominationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Settings > Money Setting."""

    queryset = Denomination.objects.all()
    serializer_class = DenominationSerializer
    permission_classes = [OwnerWriteAnyoneRead]
    pagination_class = None
