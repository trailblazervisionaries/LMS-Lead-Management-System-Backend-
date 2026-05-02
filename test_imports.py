#!/usr/bin/env python3
"""
Simple test script to validate the lead management system components.
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        # Test main app import
        from app.main import app
        print("✓ Main app imported successfully")

        # Test models
        from app.models.lead_form import FormTemplate, LeadResponse, LeadRemarks, LeadAssignment
        print("✓ Lead models imported successfully")

        # Test schemas
        from app.schemas.Lead_schemas import FormTemplateCreate, LeadCreate
        print("✓ Lead schemas imported successfully")

        # Test services
        from app.services.form_service import FormService
        from app.services.lead_service import LeadService
        print("✓ Lead services imported successfully")

        # Test routes
        from app.routes.lead_routes import router as lead_router
        print("✓ Lead routes imported successfully")

        print("\n🎉 All components imported successfully!")
        return True

    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_imports())
    sys.exit(0 if success else 1)