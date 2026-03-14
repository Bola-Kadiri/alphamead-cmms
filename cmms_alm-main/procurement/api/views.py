from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from cmms_instanta.permissions import RoleBasedPermissionMixin
from procurement.models import (
    RequestForQuotation,
    PurchaseOrder,
    PurchaseOrderRequisition,
    GoodsReceivedNote,
    VendorContract
)
from .serializers import (
    RequestForQuotationSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderRequisitionSerializer,
    GoodsReceivedNoteSerializer,
    VendorContractSerializer
)
from .response import APIResponse


class RequestForQuotationViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Request for Quotation (RFQ)
    """
    queryset = RequestForQuotation.objects.all()
    serializer_class = RequestForQuotationSerializer
    permission_classes = [IsAuthenticated]
    feature = "request_quotation"

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return APIResponse.success(
                    data=paginated_response.data,
                    message="RFQs retrieved successfully"
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="RFQs retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving RFQs: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success(
                data=serializer.data,
                message="RFQ retrieved successfully"
            )
        except Http404:
            return APIResponse.not_found(message="RFQ not found")
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving RFQ: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                errors=serializer.errors,
                message="Failed to create RFQ"
            )
        try:
            self.perform_create(serializer)
            return APIResponse.created(
                data=serializer.data,
                message="RFQ created successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to create RFQ: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if not serializer.is_valid():
                return APIResponse.validation_error(
                    errors=serializer.errors,
                    message="Failed to update RFQ"
                )
            self.perform_update(serializer)
            return APIResponse.success(
                data=serializer.data,
                message="RFQ updated successfully"
            )
        except Http404:
            return APIResponse.not_found(message="RFQ not found")
        except Exception as e:
            return APIResponse.error(
                message=f"Error updating RFQ: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse.success(
                message="RFQ deleted successfully"
            )
        except Http404:
            return APIResponse.not_found(message="RFQ not found")
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to delete RFQ: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PurchaseOrderViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Purchase Orders
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    feature = "purchase_order"

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return APIResponse.success(
                    data=paginated_response.data,
                    message="Purchase orders retrieved successfully"
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="Purchase orders retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving purchase orders: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success(
                data=serializer.data,
                message="Purchase order retrieved successfully"
            )
        except Exception as e:
            return APIResponse.not_found(message=f"Purchase order not found: {str(e)}")

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return APIResponse.created(
                data=serializer.data,
                message="Purchase order created successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to create purchase order"
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return APIResponse.success(
                data=serializer.data,
                message="Purchase order updated successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to update purchase order"
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse.success(
                message="Purchase order deleted successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to delete purchase order: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PurchaseOrderRequisitionViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Purchase Order Requisitions
    """
    queryset = PurchaseOrderRequisition.objects.all()
    serializer_class = PurchaseOrderRequisitionSerializer
    permission_classes = [IsAuthenticated]
    feature = "purchase_order_requisition"

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return APIResponse.success(
                    data=paginated_response.data,
                    message="Purchase requisitions retrieved successfully"
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="Purchase requisitions retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving purchase requisitions: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success(
                data=serializer.data,
                message="Purchase requisition retrieved successfully"
            )
        except Exception as e:
            return APIResponse.not_found(message=f"Purchase requisition not found: {str(e)}")

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return APIResponse.created(
                data=serializer.data,
                message="Purchase requisition created successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to create purchase requisition"
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return APIResponse.success(
                data=serializer.data,
                message="Purchase requisition updated successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to update purchase requisition"
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse.success(
                message="Purchase requisition deleted successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to delete purchase requisition: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoodsReceivedNoteViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Goods Received Notes (GRN)
    """
    queryset = GoodsReceivedNote.objects.all()
    serializer_class = GoodsReceivedNoteSerializer
    permission_classes = [IsAuthenticated]
    feature = "goods_received_note"

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return APIResponse.success(
                    data=paginated_response.data,
                    message="GRNs retrieved successfully"
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="GRNs retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving GRNs: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success(
                data=serializer.data,
                message="GRN retrieved successfully"
            )
        except Exception as e:
            return APIResponse.not_found(message=f"GRN not found: {str(e)}")

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return APIResponse.created(
                data=serializer.data,
                message="GRN created successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to create GRN"
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return APIResponse.success(
                data=serializer.data,
                message="GRN updated successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to update GRN"
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse.success(
                message="GRN deleted successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to delete GRN: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VendorContractViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Vendor Contracts
    """
    queryset = VendorContract.objects.all()
    serializer_class = VendorContractSerializer
    permission_classes = [IsAuthenticated]
    feature = "vendor_contract"

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return APIResponse.success(
                    data=paginated_response.data,
                    message="Vendor contracts retrieved successfully"
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="Vendor contracts retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving vendor contracts: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success(
                data=serializer.data,
                message="Vendor contract retrieved successfully"
            )
        except Exception as e:
            return APIResponse.not_found(message=f"Vendor contract not found: {str(e)}")

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return APIResponse.created(
                data=serializer.data,
                message="Vendor contract created successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to create vendor contract"
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return APIResponse.success(
                data=serializer.data,
                message="Vendor contract updated successfully"
            )
        except Exception as e:
            return APIResponse.validation_error(
                errors=serializer.errors if 'serializer' in locals() else {"error": str(e)},
                message="Failed to update vendor contract"
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse.success(
                message="Vendor contract deleted successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to delete vendor contract: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
