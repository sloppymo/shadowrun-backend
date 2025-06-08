#!/usr/bin/env python3
"""
Environment Variable Checker for Shadowrun RPG System
Ensures all required environment variables are set before deployment
"""

import os
import sys
from typing import List, Tuple, Dict

# Required environment variables
REQUIRED_VARS = {
    # Core Configuration
    'FLASK_ENV': 'Flask environment (development/production)',
    'SECRET_KEY': 'Flask secret key for sessions',
    'DATABASE_URL': 'Database connection string',
    
    # Authentication
    'CLERK_API_KEY': 'Clerk authentication API key',
    'CLERK_SECRET_KEY': 'Clerk secret key',
    
    # AI Services
    'OPENAI_API_KEY': 'OpenAI API key for GPT/DALL-E',
    'ANTHROPIC_API_KEY': 'Anthropic API key for Claude',
    
    # Image Generation
    'STABILITY_API_KEY': 'Stability AI API key (optional)',
    'REPLICATE_API_TOKEN': 'Replicate API token (optional)',
    
    # Slack Integration
    'SLACK_BOT_TOKEN': 'Slack bot user token',
    'SLACK_SIGNING_SECRET': 'Slack request signing secret',
    'SLACK_APP_TOKEN': 'Slack app-level token (optional)',
    
    # External Services
    'REDIS_URL': 'Redis connection URL (optional)',
    'SENTRY_DSN': 'Sentry error tracking DSN (optional)',
    
    # Security
    'ALLOWED_ORIGINS': 'CORS allowed origins',
    'SESSION_COOKIE_SECURE': 'Secure cookie flag (True for production)',
    'SESSION_COOKIE_HTTPONLY': 'HttpOnly cookie flag',
    'SESSION_COOKIE_SAMESITE': 'SameSite cookie policy'
}

# Optional but recommended variables
OPTIONAL_VARS = {
    'LOG_LEVEL': 'Logging level (DEBUG/INFO/WARNING/ERROR)',
    'MAX_CONTENT_LENGTH': 'Maximum request size in bytes',
    'RATE_LIMIT_STORAGE_URL': 'Redis URL for rate limiting',
    'CACHE_TYPE': 'Cache backend type',
    'MAIL_SERVER': 'Email server for notifications',
    'MAIL_USERNAME': 'Email username',
    'MAIL_PASSWORD': 'Email password',
    'AWS_ACCESS_KEY_ID': 'AWS access key for S3',
    'AWS_SECRET_ACCESS_KEY': 'AWS secret key',
    'S3_BUCKET': 'S3 bucket for file storage'
}

def check_environment() -> Tuple[List[str], List[str], Dict[str, str]]:
    """Check environment variables and return status"""
    missing_required = []
    missing_optional = []
    warnings = {}
    
    # Check required variables
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_required.append(f"{var}: {description}")
        else:
            # Additional validation
            if var == 'FLASK_ENV' and value not in ['development', 'production', 'testing']:
                warnings[var] = f"Invalid value '{value}'. Should be development/production/testing"
            
            if var == 'SECRET_KEY' and len(value) < 32:
                warnings[var] = "Secret key should be at least 32 characters long"
            
            if var.endswith('_API_KEY') and value.startswith('sk-'):
                if len(value) < 20:
                    warnings[var] = "API key seems too short"
    
    # Check optional variables
    for var, description in OPTIONAL_VARS.items():
        if not os.getenv(var):
            missing_optional.append(f"{var}: {description}")
    
    return missing_required, missing_optional, warnings

def generate_env_template() -> str:
    """Generate .env template content"""
    template = "# Shadowrun RPG System Environment Variables\n\n"
    
    template += "# === REQUIRED VARIABLES ===\n\n"
    for var, desc in REQUIRED_VARS.items():
        template += f"# {desc}\n"
        template += f"{var}=\n\n"
    
    template += "\n# === OPTIONAL VARIABLES ===\n\n"
    for var, desc in OPTIONAL_VARS.items():
        template += f"# {desc}\n"
        template += f"# {var}=\n\n"
    
    return template

def main():
    """Main entry point"""
    print("🔍 Checking environment variables for Shadowrun RPG System...")
    print("=" * 60)
    
    missing_required, missing_optional, warnings = check_environment()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  No .env file found!")
        print("Creating .env.example template...")
        
        with open('.env.example', 'w') as f:
            f.write(generate_env_template())
        
        print("✅ Created .env.example - copy it to .env and fill in values")
        print()
    
    # Report results
    if missing_required:
        print("❌ MISSING REQUIRED VARIABLES:")
        for var in missing_required:
            print(f"   - {var}")
        print()
    else:
        print("✅ All required variables are set")
        print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for var, warning in warnings.items():
            print(f"   - {var}: {warning}")
        print()
    
    if missing_optional:
        print("📋 Missing optional variables (recommended for production):")
        for var in missing_optional[:5]:  # Show first 5
            print(f"   - {var}")
        if len(missing_optional) > 5:
            print(f"   ... and {len(missing_optional) - 5} more")
        print()
    
    # Environment-specific checks
    flask_env = os.getenv('FLASK_ENV', 'development')
    print(f"🌍 Current environment: {flask_env}")
    
    if flask_env == 'production':
        print("\n🚀 PRODUCTION ENVIRONMENT CHECKS:")
        
        prod_issues = []
        
        if os.getenv('DEBUG', '').lower() == 'true':
            prod_issues.append("DEBUG is enabled - should be False in production")
        
        if not os.getenv('SESSION_COOKIE_SECURE', '').lower() == 'true':
            prod_issues.append("SESSION_COOKIE_SECURE should be True")
        
        if not os.getenv('SENTRY_DSN'):
            prod_issues.append("SENTRY_DSN not set - error tracking recommended")
        
        if not os.getenv('REDIS_URL'):
            prod_issues.append("REDIS_URL not set - caching/rate limiting may not work")
        
        if prod_issues:
            print("❌ Production issues found:")
            for issue in prod_issues:
                print(f"   - {issue}")
        else:
            print("✅ Production configuration looks good")
    
    print("\n" + "=" * 60)
    
    # Exit with appropriate code
    if missing_required:
        print("❌ Environment check FAILED - missing required variables")
        sys.exit(1)
    elif warnings or (flask_env == 'production' and missing_optional):
        print("⚠️  Environment check PASSED with warnings")
        sys.exit(0)
    else:
        print("✅ Environment check PASSED")
        sys.exit(0)

if __name__ == '__main__':
    main() 