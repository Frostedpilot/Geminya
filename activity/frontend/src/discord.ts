import { DiscordSDK } from '@discord/embedded-app-sdk'

const CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID || ''

export interface DiscordUser {
    id: string
    username: string
    discriminator: string
    avatar: string | null
}

let discordSdk: DiscordSDK | null = null

export async function setupDiscord(): Promise<DiscordUser> {
    if (!CLIENT_ID) {
        throw new Error('Discord Client ID not configured')
    }

    discordSdk = new DiscordSDK(CLIENT_ID)
    await discordSdk.ready()

    const { code } = await discordSdk.commands.authorize({
        client_id: CLIENT_ID,
        response_type: 'code',
        state: '',
        prompt: 'none',
        scope: ['identify'],
    })

    const auth = await discordSdk.commands.authenticate({ access_token: code })

    if (!auth.user) {
        throw new Error('Failed to get user info from Discord')
    }

    return {
        id: auth.user.id,
        username: auth.user.username,
        discriminator: auth.user.discriminator ?? '0000',
        avatar: auth.user.avatar ?? null,
    }
}

export function getDiscordSdk(): DiscordSDK | null {
    return discordSdk
}
