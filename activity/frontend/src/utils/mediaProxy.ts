/**
 * Proxy external media URLs through the backend to bypass Discord CSP
 */
export function proxyMediaUrl(url: string | null | undefined): string {
    if (!url) return ''
    
    // If it's already a proxied URL or a data URL, return as-is
    if (url.startsWith('/api/media/proxy') || url.startsWith('data:')) {
        return url
    }
    
    // If it's a Discord CDN URL, allow it directly
    if (url.includes('cdn.discordapp.com') || url.includes('media.discordapp.net')) {
        return url
    }
    
    // Proxy all other external URLs
    return `/api/media/proxy?url=${encodeURIComponent(url)}`
}
