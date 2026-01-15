# Role-Based Access Control (RBAC) System 

Author: Antor Ahmed
Time: 2026-01-12

## Features Implemented

### 2026-01-12 Updates
- Role claim is required in every JWT; missing or invalid roles now fail authentication.
- Custom token endpoint `wcapi/token/` issues role-aware access and refresh tokens.
- Authentication rejects tokens whose role no longer matches the database, so admin-panel role changes take effect after re-login.
- Data visibility is enforced per role via query constraints:
	- `admin`: full access.
	- `employee`: same data visibility as admin, but cannot assign the `admin` role through save APIs.
	- `user`: only own/assigned data (created_by/contact/owner/user/assigned_to/assignee/shared_with when present); otherwise no access.
- Save API applies the same constraints on updates, stamps ownership fields to the acting user when present, and prevents users from reassigning ownership away from themselves.

### 1. Role Model Restriction
- Only three roles are supported: **Admin**, **Employee**, and **User**.
- The `Contact` model and all role logic now only accept these three roles.

### 2. JWT Authentication with Role Claim
- JWT tokens (access and refresh) now include the user's `role` in their claims.
- Role is set at login and registration, and is always available in the token payload.
- JWT tokens have expiry (7 days for access, 30 days for refresh).

### 3. Permissions and Enforcement
- All role-based permission logic is updated to only recognize Admin, Employee, and User.
- `Admin`: Full access to all data and actions.
- `Employee`: Can view all, edit most, but not all admin actions.
- `User`: Can only view/edit their own data and limited fields.
- All API endpoints can check the user's role from the JWT token for access control.

### 4. API Changes
- Login and registration endpoints now return the user's role in the response and in the JWT.
- Role is enforced at user creation (default is `user`).
- Only admins can assign or change roles to `admin` or `employee`.
- Token obtain endpoint now uses the role-aware serializer (`wcapi/token/`), embedding role into access and refresh tokens; refresh keeps the role claim.

### 5. Codebase Changes
- `apps/core/choices.py`: Only three roles are defined in `CONTACT_ROLE_CHOICES`.
- `apps/core/permissions.py`: All permission logic and field access rules updated for the three roles.
- `apps/core/views/auth_views.py`: JWT tokens now include the role claim; role is returned in login/register responses.
- `apps/core/auth.py`: Role claim is required and validated against the database; role-aware token obtain serializer/view added.
- `apps/core/urls.py`: Token obtain endpoint swapped to the role-aware view.
- `apps/core/utils/policy.py`: Query constraints scope data by role (full for admin/employee; own/assigned only for user).
- `apps/core/views/save_view.py`: Save operations honor the same constraints, auto-stamp ownership fields, and prevent employees from assigning the admin role.

### 6. Security
- All role checks are enforced both at the model and API level.
- JWT expiry is enforced (configurable in settings).

## Usage
- Register/login as usual. The JWT token will include your role.
- Use the JWT as `Bearer` in the `Authorization` header for all API requests.
- The backend will enforce access based on your role.

---
*Author: Antor Ahmed*
*Date: 2026-01-12*
