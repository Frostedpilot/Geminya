#!/usr/bin/env python3
"""MyAnimeList API service for OAuth and user data fetching."""

import aiohttp
import asyncio
import base64
import json
import secrets
import urllib.parse
from typing import Dict, List, Optional, Any
import logging


class MALAPIService:
    """Service for interacting with MyAnimeList API v2."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.myanimelist.net/v2"
        self.auth_url = "https://myanimelist.net/v1/oauth2"
        self.session = None
        self.access_token = None
        self.refresh_token = None
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def generate_auth_url(
        self, redirect_uri: str, state: str = None
    ) -> tuple[str, str]:
        """Generate OAuth authorization URL and code verifier."""
        # Generate PKCE code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        # For MAL, code_challenge = code_verifier (plain method)
        code_challenge = code_verifier

        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "state": state,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "plain",
        }

        auth_url = f"{self.auth_url}/authorize?" + urllib.parse.urlencode(params)
        return auth_url, code_verifier

    async def exchange_code_for_tokens(
        self, authorization_code: str, redirect_uri: str, code_verifier: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        # Prepare authentication header
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }

        async with self.session.post(
            f"{self.auth_url}/token", headers=headers, data=data
        ) as response:
            result = await response.json()

            if response.status == 200:
                self.access_token = result["access_token"]
                self.refresh_token = result["refresh_token"]
                return result
            else:
                raise Exception(f"Token exchange failed: {result}")

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh the access token using refresh token."""
        if not self.refresh_token:
            raise RuntimeError("No refresh token available")

        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}

        async with self.session.post(
            f"{self.auth_url}/token", headers=headers, data=data
        ) as response:
            result = await response.json()

            if response.status == 200:
                self.access_token = result["access_token"]
                return result
            else:
                raise Exception(f"Token refresh failed: {result}")

    async def _make_authenticated_request(
        self, endpoint: str, params: Dict = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to MAL API."""
        if not self.access_token:
            raise RuntimeError("No access token available. Complete OAuth flow first.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status == 401:
                # Try to refresh token
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"

                async with self.session.get(
                    url, headers=headers, params=params
                ) as retry_response:
                    return await retry_response.json()

            return await response.json()

    async def get_user_anime_list(
        self, username: str = "@me", status: str = None
    ) -> List[Dict[str, Any]]:
        """Get user's anime list."""
        params = {
            "fields": "id,title,main_picture,mean,genres,media_type,status,start_date,end_date",
            "limit": 1000,  # Maximum allowed
        }

        if status:
            params["status"] = status

        endpoint = f"/users/{username}/animelist"
        result = await self._make_authenticated_request(endpoint, params)

        anime_list = []
        if "data" in result:
            for item in result["data"]:
                anime_list.append(item["node"])

        return anime_list

    async def get_user_manga_list(
        self, username: str = "@me", status: str = None
    ) -> List[Dict[str, Any]]:
        """Get user's manga list."""
        params = {
            "fields": "id,title,main_picture,mean,genres,media_type,status,start_date,end_date",
            "limit": 1000,  # Maximum allowed
        }

        if status:
            params["status"] = status

        endpoint = f"/users/{username}/mangalist"
        result = await self._make_authenticated_request(endpoint, params)

        manga_list = []
        if "data" in result:
            for item in result["data"]:
                manga_list.append(item["node"])

        return manga_list

    async def get_user_profile(self, username: str = "@me") -> Dict[str, Any]:
        """Get user profile information."""
        endpoint = f"/users/{username}"
        params = {"fields": "id,name,location,joined_at"}

        return await self._make_authenticated_request(endpoint, params)
