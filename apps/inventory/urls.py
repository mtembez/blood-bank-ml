from django.urls import path
from apps.inventory.views import InventoryListCreateView, InventorySummaryView

app_name = "inventory"

urlpatterns = [
    path("", InventoryListCreateView.as_view(), name="inventory-list-create"),
    path("summary", InventorySummaryView.as_view(), name="inventory-summary"),
]
