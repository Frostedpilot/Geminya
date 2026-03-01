"""Media proxy router for external images/videos to bypass Discord CSP."""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
import aiohttp
from urllib.parse import unquote

router = APIRouter()


@router.get("/proxy")
async def proxy_media(url: str):
    """Proxy external media through the backend to bypass Discord CSP.
    
    Usage: /media/proxy?url=https://external-site.com/image.jpg
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter required")
    
    # Decode URL if it's encoded
    url = unquote(url)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch media")
                
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                content = await response.read()
                
                return Response(
                    content=content,
                    media_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                        'Access-Control-Allow-Origin': '*'
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to proxy media: {str(e)}")
