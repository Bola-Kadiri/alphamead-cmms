# serializers.py
from rest_framework import serializers
from work.models import PPM
from datetime import datetime, timedelta
import calendar

class PPMCalendarSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    
    class Meta:
        model = PPM
        fields = ['id', 'title', 'start', 'end', 'color', 'description', 'frequency', 'frequency_unit']
    
    def get_title(self, obj):
        return f"PPM: {obj.description[:30]}..." if len(obj.description) > 30 else f"PPM: {obj.description}"
    
    def get_start(self, obj):
        # This would normally use actual scheduled dates
        # For demo, we'll use created date as a starting point
        return obj.created_at.strftime("%Y-%m-%dT%H:%M:%S")
    
    def get_end(self, obj):
        # Calculate end date based on frequency and unit
        start_date = obj.created_at
        if obj.frequency_unit == 'Hours':
            end_date = start_date + timedelta(hours=obj.frequency)
        elif obj.frequency_unit == 'Days':
            end_date = start_date + timedelta(days=obj.frequency)
        elif obj.frequency_unit == 'Weeks':
            end_date = start_date + timedelta(weeks=obj.frequency)
        elif obj.frequency_unit == 'Months':
            # Calculate months by getting new year and month
            new_month = start_date.month + obj.frequency
            new_year = start_date.year + new_month // 12
            new_month = new_month % 12 if new_month % 12 else 12
            
            # Get last day of the new month
            last_day = calendar.monthrange(new_year, new_month)[1]
            day = min(start_date.day, last_day)
            
            end_date = start_date.replace(year=new_year, month=new_month, day=day)
        else:
            end_date = start_date
            
        return end_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    def get_color(self, obj):
        # Generate a color based on the status or category
        status_colors = {
            'pending': '#FFC107',  # Yellow
            'in_progress': '#2196F3',  # Blue
            'completed': '#4CAF50',  # Green
            'overdue': '#F44336',  # Red
        }
        
        # Assuming 'status' is a field from the Status model mixin
        # If not present, default to a random color
        status = getattr(obj, 'status', None)
        if status and status in status_colors:
            return status_colors[status]
        
        # Use category id to determine color if no status
        if obj.category_id:
            # Generate colors based on category ID to ensure consistency
            colors = ['#4285F4', '#34A853', '#FBBC05', '#EA4335', '#8E24AA', '#00ACC1']
            return colors[obj.category_id % len(colors)]
            
        return '#607D8B'  # Default gray