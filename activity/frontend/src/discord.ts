import { DiscordSDK } from '@discord/embedded-app-sdk'

const CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID || ''

export interface DiscordUser {
    id: string
    username: string
    discriminator: string
    avatar: string | null
    global_name?: string | null
}

let discordSdk: DiscordSDK | null = null

export async function setupDiscord(): Promise<DiscordUser> {
    if (!CLIENT_ID) {
        throw new Error('Discord Client ID not configured')
    }

    console.log('Initializing Discord SDK with Client ID:', CLIENT_ID)

    discordSdk = new DiscordSDK(CLIENT_ID)

    console.log('Waiting for SDK ready...')
    await discordSdk.ready()
    console.log('SDK ready!')

    // Step 1: Authorize - get OAuth2 code
    const { code } = await discordSdk.commands.authorize({
        client_id: CLIENT_ID,
        response_type: 'code',
        state: '',
        prompt: 'none',
        scope: ['identify', 'guilds'],
    })

    console.log('Authorization complete, exchanging code for token...')

    // Step 2: Exchange code for access token via backend
    const tokenResponse = await fetch('/api/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
    })

    if (!tokenResponse.ok) {
        console.error('Token exchange failed:', tokenResponse.status)
        throw new Error('Failed to exchange token')
    }

    const { access_token } = await tokenResponse.json()
    console.log('Token exchange successful')

    // Step 3: Authenticate with the SDK using the access token
    const auth = await discordSdk.commands.authenticate({ access_token })
    console.log('Authenticated! User:', auth.user.username)

    // Build avatar URL
    const user = auth.user
    let avatarUrl: string | null = null
    if (user.avatar) {
        avatarUrl = `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=128`
    }

    return {
        id: user.id,
        username: user.username,
        discriminator: user.discriminator || '0',
        avatar: avatarUrl,
        global_name: user.global_name || null,
    }
}

export function getDiscordSdk(): DiscordSDK | null {
    return discordSdk
}
