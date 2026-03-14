#!/usr/bin/env python
"""
Reset Django database on DigitalOcean managed database
This script drops all tables and removes migration files
"""
import os
import sys
import django
from django.core.management import call_command
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmms_instanta.settings')  # Replace with your project name
django.setup()

def drop_all_tables():
    """Drop all tables in the database"""
    with connection.cursor() as cursor:
        # Get all table names
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = cursor.fetchall()
        
        # Drop each table
        for table in tables:
            table_name = table[0]
            print(f"Dropping table: {table_name}")
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
        
        print(f"\n✅ Dropped {len(tables)} tables")

def clean_migrations():
    """Remove all migration files except __init__.py"""
    migrations_deleted = 0
    
    for root, dirs, files in os.walk('.'):
        if 'migrations' in dirs:
            migrations_dir = os.path.join(root, 'migrations')
            for filename in os.listdir(migrations_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    filepath = os.path.join(migrations_dir, filename)
                    os.remove(filepath)
                    migrations_deleted += 1
                elif filename.endswith('.pyc'):
                    filepath = os.path.join(migrations_dir, filename)
                    os.remove(filepath)
    
    print(f"✅ Deleted {migrations_deleted} migration files")

def recreate_database():
    """Recreate migrations and apply them"""
    print("\n📦 Creating new migrations...")
    call_command('makemigrations')
    
    print("\n🚀 Applying migrations...")
    call_command('migrate')
    
    print("\n✅ Database recreated successfully!")

if __name__ == "__main__":
    print("⚠️  WARNING: This will DELETE ALL DATA in your database!")
    print("Database:", os.environ.get('DATABASE_URL', 'Check settings.py'))
    response = input("\nType 'yes' to continue: ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
    try:
        print("\n🗑️  Dropping all tables...")
        drop_all_tables()
        
        print("\n🧹 Cleaning migration files...")
        clean_migrations()
        
        print("\n🔨 Recreating database...")
        recreate_database()
        
        print("\n✨ All done! You may want to run 'python manage.py createsuperuser'")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
