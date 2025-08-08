# Eunice Research Platform Roadmap

## Overview

This is the development roadmap for the Eunice Research Platform.

## Version 0.4.0

[X] Platform redesign to be AI prompt driven.
[ ] Implement frontend API calls for direct database read and write.
    - `create_project`, `update_project`, `delete_project`
    - `create_research_topic`, `update_research_topic`, `delete_research_topic`
    - `update_research_plan`, `delete_research_plan`, `approve_research_plan`
[ ] Unit test all functional API calls on the API Gateway.    

## Version 0.4.1

[ ] Implement `create_research_plan` function.
[ ] Authentication function for all APIs.
    - Authentication Features:
        - JWT access tokens (30 min) and refresh tokens (7 days)
        - TOTP-based 2FA with Google/Microsoft Authenticator support
        - Password strength validation with real-time feedback
        - Email and username-based login support
        - Backup codes for 2FA account recovery
    - RBAC System:
        - Admin: Full system access (*:*)
        - Researcher: Literature, research, planning, memory operations
        - Collaborator: Read-only access with commenting capabilities
    - Security Implementation:
        - bcrypt password hashing with automatic salt generation
        - JWT signed with HMAC SHA-256 (RFC 7519 compliant)
        - Rate limiting and brute force protection ready
        - CORS configured for frontend integration
    - Container Security:
        - Non-root user execution
        - Read-only filesystem
        - Dropped Linux capabilities
        - Resource limits and health checks