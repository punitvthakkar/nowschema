"""
SSO service using WorkOS.
Handles enterprise SAML/OIDC authentication.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

try:
    import workos
    from workos import WorkOSClient
except ImportError:
    workos = None
    WorkOSClient = None

from .database import DatabaseService, User, Tenant


@dataclass
class SSOProfile:
    """SSO user profile from identity provider."""
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    raw_attributes: Dict[str, Any]
    connection_id: str
    connection_type: str  # SAML, OIDC
    organization_id: Optional[str]


@dataclass
class SSOConnection:
    """SSO connection configuration."""
    id: str
    name: str
    connection_type: str
    state: str  # active, inactive
    domains: list
    organization_id: str


class SSOService:
    """Service for SSO operations using WorkOS."""

    def __init__(
        self,
        db: DatabaseService,
        workos_api_key: str,
        workos_client_id: str,
        redirect_uri: str,
    ):
        """
        Initialize SSO service.

        Args:
            db: Database service instance
            workos_api_key: WorkOS API key
            workos_client_id: WorkOS client ID
            redirect_uri: OAuth callback URL
        """
        if WorkOSClient is None:
            raise RuntimeError("workos not available")

        self.db = db
        self.client = WorkOSClient(api_key=workos_api_key)
        self.client_id = workos_client_id
        self.redirect_uri = redirect_uri

    # ==================== SSO AUTHENTICATION ====================

    def get_authorization_url(
        self,
        domain: str = None,
        connection_id: str = None,
        organization_id: str = None,
        state: str = None,
    ) -> str:
        """
        Get the SSO authorization URL.

        Provide one of: domain, connection_id, or organization_id.

        Args:
            domain: User's email domain for domain-based SSO
            connection_id: Specific SSO connection ID
            organization_id: WorkOS organization ID
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }

        if domain:
            params["domain"] = domain
        elif connection_id:
            params["connection"] = connection_id
        elif organization_id:
            params["organization"] = organization_id
        else:
            raise ValueError("Must provide domain, connection_id, or organization_id")

        if state:
            params["state"] = state

        return self.client.sso.get_authorization_url(**params)

    async def handle_callback(
        self,
        code: str,
    ) -> Tuple[SSOProfile, Optional[User], Optional[Tenant]]:
        """
        Handle SSO callback and authenticate user.

        Args:
            code: Authorization code from callback

        Returns:
            Tuple of (SSOProfile, User if exists, Tenant if exists)
        """
        # Exchange code for profile
        profile_and_token = self.client.sso.get_profile_and_token(code)
        workos_profile = profile_and_token.profile

        sso_profile = SSOProfile(
            id=workos_profile.id,
            email=workos_profile.email,
            first_name=workos_profile.first_name,
            last_name=workos_profile.last_name,
            raw_attributes=workos_profile.raw_attributes,
            connection_id=workos_profile.connection_id,
            connection_type=workos_profile.connection_type,
            organization_id=workos_profile.organization_id,
        )

        # Check if user exists
        user = await self.db.get_user_by_workos_id(sso_profile.id)

        # Check for tenant by SSO domain
        email_domain = sso_profile.email.split("@")[1] if "@" in sso_profile.email else None
        tenant = None
        if email_domain:
            tenant = await self.db.get_tenant_by_domain(email_domain)

        return sso_profile, user, tenant

    async def provision_user(
        self,
        profile: SSOProfile,
        tenant_id: str,
    ) -> User:
        """
        Just-in-time provision a new user from SSO.

        Args:
            profile: SSO profile from identity provider
            tenant_id: Tenant to add user to

        Returns:
            Newly created user
        """
        return await self.db.create_user(
            tenant_id=tenant_id,
            email=profile.email,
            auth_provider="sso",
            role="member",
            workos_user_id=profile.id,
        )

    # ==================== CONNECTION MANAGEMENT ====================

    async def create_organization(
        self,
        tenant_id: str,
        tenant_name: str,
        domains: list,
    ) -> str:
        """
        Create a WorkOS organization for a tenant.

        Args:
            tenant_id: The tenant ID
            tenant_name: Name for the organization
            domains: List of email domains for the organization

        Returns:
            WorkOS organization ID
        """
        org = self.client.organizations.create_organization(
            name=tenant_name,
            domains=domains,
        )

        # Update tenant with SSO info
        await self.db.update_tenant(tenant_id, {
            "sso_enabled": True,
            "sso_domain": domains[0] if domains else None,
        })

        return org.id

    async def get_connections(self, organization_id: str) -> list:
        """Get SSO connections for an organization."""
        connections = self.client.sso.list_connections(
            organization_id=organization_id
        )
        return [
            SSOConnection(
                id=conn.id,
                name=conn.name,
                connection_type=conn.connection_type,
                state=conn.state,
                domains=conn.domains or [],
                organization_id=conn.organization_id,
            )
            for conn in connections.data
        ]

    async def get_connection(self, connection_id: str) -> Optional[SSOConnection]:
        """Get a specific SSO connection."""
        try:
            conn = self.client.sso.get_connection(connection_id)
            return SSOConnection(
                id=conn.id,
                name=conn.name,
                connection_type=conn.connection_type,
                state=conn.state,
                domains=conn.domains or [],
                organization_id=conn.organization_id,
            )
        except Exception:
            return None

    # ==================== DIRECTORY SYNC ====================

    async def sync_directory_user(
        self,
        directory_user: Dict[str, Any],
        tenant_id: str,
    ) -> User:
        """
        Sync a user from directory (SCIM).

        Args:
            directory_user: User data from WorkOS directory
            tenant_id: Tenant to sync to

        Returns:
            Created or updated user
        """
        email = directory_user.get("emails", [{}])[0].get("value", "")
        workos_id = directory_user.get("idp_id", "")

        # Check if user exists
        existing = await self.db.get_user_by_workos_id(workos_id)

        if existing:
            # Update existing user
            return await self.db.update_user(existing.id, {
                "email": email,
                "status": "active" if directory_user.get("state") == "active" else "suspended",
            })
        else:
            # Create new user
            return await self.db.create_user(
                tenant_id=tenant_id,
                email=email,
                auth_provider="sso",
                role="member",
                workos_user_id=workos_id,
            )

    # ==================== DOMAIN DETECTION ====================

    async def detect_sso_domain(self, email: str) -> Optional[Tenant]:
        """
        Check if an email domain has SSO configured.

        Args:
            email: User's email address

        Returns:
            Tenant with SSO if found, None otherwise
        """
        if "@" not in email:
            return None

        domain = email.split("@")[1].lower()
        tenant = await self.db.get_tenant_by_domain(domain)

        if tenant and tenant.sso_enabled:
            return tenant

        return None

    def should_redirect_to_sso(self, email: str, tenant: Optional[Tenant]) -> bool:
        """
        Determine if user should be redirected to SSO.

        Args:
            email: User's email
            tenant: Tenant if found by domain

        Returns:
            True if should redirect to SSO
        """
        if not tenant:
            return False

        if not tenant.sso_enabled:
            return False

        # Check if email domain matches SSO domain
        if "@" in email:
            domain = email.split("@")[1].lower()
            if tenant.sso_domain and tenant.sso_domain.lower() == domain:
                return True

        return False
