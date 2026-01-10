# Role-Based Access Control (RBAC) System 

Author: Antor Ahmed
Time: 2026-01-10

## Features Implemented

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

### 5. Codebase Changes
- `apps/core/choices.py`: Only three roles are defined in `CONTACT_ROLE_CHOICES`.
- `apps/core/permissions.py`: All permission logic and field access rules updated for the three roles.
- `apps/core/views/auth_views.py`: JWT tokens now include the role claim; role is returned in login/register responses.

### 6. Security
- All role checks are enforced both at the model and API level.
- JWT expiry is enforced (configurable in settings).

## Usage
- Register/login as usual. The JWT token will include your role.
- Use the JWT as `Bearer` in the `Authorization` header for all API requests.
- The backend will enforce access based on your role.

---
*Author: Antor Ahmed*
*Date: 2026-01-10*
