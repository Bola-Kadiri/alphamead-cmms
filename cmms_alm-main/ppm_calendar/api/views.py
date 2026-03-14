# views.py
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from work.models import PPM
from .serializers import PPMCalendarSerializer

from cmms_instanta.permissions import RoleBasedPermissionMixin


class PPMCalendarViewSet(RoleBasedPermissionMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PPM.objects.all()
    serializer_class = PPMCalendarSerializer
    # permission_classes = [permissions.IsAuthenticated]
    feature = "ppm_setting"
    
    # def get_queryset(self):
    #     """
    #     Filter PPMs based on user permissions.
    #     """
    #     # Assuming OwnerPrivModel handles permissions
    #     return super().get_queryset().filter_for_user(self.request.user)
    
    def get_queryset(self):
        """
        Filter PPMs based on user permissions.
        """
        # Prevent errors during schema generation
        if getattr(self, 'swagger_fake_view', False):
             return PPM.objects.none()
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)

    
    @action(detail=False, methods=['get'])
    def calendar_events(self, request):
        """
        Get PPM events for the specified date range.
        """
        # Get date range parameters
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        
        # Default to current month if not specified
        if not start_date:
            today = timezone.now()
            start_date = timezone.make_aware(datetime(today.year, today.month, 1))
        else:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
        
        if not end_date:
            end_date = start_date + relativedelta(months=1)
        else:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
        
        # Get base PPMs
        ppms = self.get_queryset()
        
        # Generate recurring events
        calendar_events = []
        for ppm in ppms:
            # Start with the original creation date (ensure it's timezone-aware)
            current_date = ppm.created_at
            if timezone.is_naive(current_date):
                current_date = timezone.make_aware(current_date)
            
            # Generate recurring events until end_date
            while current_date < end_date:
                # Only include events that fall within the requested range
                if current_date >= start_date:
                    # Calculate end time
                    if ppm.frequency_unit == 'Hours':
                        event_end = current_date + timedelta(hours=ppm.frequency)
                    elif ppm.frequency_unit == 'Days':
                        event_end = current_date + timedelta(days=ppm.frequency)
                    elif ppm.frequency_unit == 'Weeks':
                        event_end = current_date + timedelta(weeks=ppm.frequency)
                    elif ppm.frequency_unit == 'Months':
                        event_end = current_date + relativedelta(months=ppm.frequency)
                    else:
                        event_end = current_date + timedelta(days=1)
                    
                    calendar_events.append({
                        'id': ppm.id,
                        'title': f"PPM: {ppm.description[:30]}..." if len(ppm.description) > 30 else f"PPM: {ppm.description}",
                        'start': current_date.strftime("%Y-%m-%dT%H:%M:%S"),
                        'end': event_end.strftime("%Y-%m-%dT%H:%M:%S"),
                        'color': self._get_event_color(ppm),
                        'description': ppm.description,
                        'category': ppm.category.title if ppm.category else None,
                        'frequency': f"{ppm.frequency} {ppm.frequency_unit}"
                    })
                
                # Move to next occurrence based on frequency
                if ppm.frequency_unit == 'Hours':
                    current_date += timedelta(hours=ppm.frequency)
                elif ppm.frequency_unit == 'Days':
                    current_date += timedelta(days=ppm.frequency)
                elif ppm.frequency_unit == 'Weeks':
                    current_date += timedelta(weeks=ppm.frequency)
                elif ppm.frequency_unit == 'Months':
                    current_date += relativedelta(months=ppm.frequency)
                else:
                    break
        
        return Response(calendar_events)

    def _get_event_color(self, ppm):
        """Helper method to determine the color of an event based on its status."""
        status_colors = {
            'pending': '#FFC107',  # Yellow
            'in_progress': '#2196F3',  # Blue
            'completed': '#4CAF50',  # Green
            'overdue': '#F44336',  # Red
        }
        
        status = getattr(ppm, 'status', None)
        if status and status in status_colors:
            return status_colors[status]
        
        # Use category id to determine color if no status
        if ppm.category_id:
            colors = ['#4285F4', '#34A853', '#FBBC05', '#EA4335', '#8E24AA', '#00ACC1']
            return colors[ppm.category_id % len(colors)]
            
        return '#607D8B'  # Default gray
      
      
      # Additional view method for the PPMCalendarViewSet

@action(detail=False, methods=['get'])
def month_view(self, request):
    """
    Get PPM events for a specific month.
    """
    # Get the year and month from request parameters
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    
    try:
        year = int(year) if year else timezone.now().year
        month = int(month) if month else timezone.now().month
    except ValueError:
        return Response({"error": "Invalid year or month format"}, status=400)
    
    # Calculate start and end dates for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get PPMs
    ppms = self.get_queryset()
    
    # Generate calendar events for the month
    calendar_events = []
    for ppm in ppms:
        current_date = ppm.created_at
        
        # Generate recurring events until end_date
        while current_date < end_date:
            if current_date >= start_date:
                if ppm.frequency_unit == 'Hours':
                    event_end = current_date + timedelta(hours=ppm.frequency)
                elif ppm.frequency_unit == 'Days':
                    event_end = current_date + timedelta(days=ppm.frequency)
                elif ppm.frequency_unit == 'Weeks':
                    event_end = current_date + timedelta(weeks=ppm.frequency)
                elif ppm.frequency_unit == 'Months':
                    event_end = current_date + relativedelta(months=ppm.frequency)
                else:
                    event_end = current_date + timedelta(days=1)
                
                calendar_events.append({
                    'id': ppm.id,
                    'title': f"PPM: {ppm.description[:30]}..." if len(ppm.description) > 30 else f"PPM: {ppm.description}",
                    'start': current_date.strftime("%Y-%m-%d"),
                    'end': event_end.strftime("%Y-%m-%d"),
                    'color': self._get_event_color(ppm),
                    'description': ppm.description,
                    'assets': list(ppm.assets.values_list('name', flat=True)),
                    'facilities': list(ppm.facilities.values_list('name', flat=True)),
                    'allDay': True
                })
            
            # Move to next occurrence
            if ppm.frequency_unit == 'Hours':
                current_date += timedelta(hours=ppm.frequency)
            elif ppm.frequency_unit == 'Days':
                current_date += timedelta(days=ppm.frequency)
            elif ppm.frequency_unit == 'Weeks':
                current_date += timedelta(weeks=ppm.frequency)
            elif ppm.frequency_unit == 'Months':
                current_date += relativedelta(months=ppm.frequency)
            else:
                break
    
    return Response(calendar_events)