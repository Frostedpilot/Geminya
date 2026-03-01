import { Link, useLocation } from 'react-router-dom'

const games = [
    {
        id: 'anidle',
        name: 'Anidle',
        emoji: '🎯',
        path: '/anidle',
    },
    {
        id: 'guess-anime',
        name: 'Guess Anime',
        emoji: '📸',
        path: '/guess-anime',
    },
    {
        id: 'guess-character',
        name: 'Guess Character',
        emoji: '🎭',
        path: '/guess-character',
    },
    {
        id: 'guess-opening',
        name: 'Guess OP',
        emoji: '🎵',
        path: '/guess-opening',
    },
    {
        id: 'guess-ending',
        name: 'Guess ED',
        emoji: '🎶',
        path: '/guess-ending',
    },
]

export default function Sidebar() {
    const location = useLocation()

    return (
        <div className="fixed left-0 top-0 h-full w-48 bg-black/40 backdrop-blur-lg border-r border-white/10 flex flex-col py-6 px-3 z-50">
            {/* Logo/Home */}
            <Link
                to="/"
                className={`w-full h-12 rounded-xl flex items-center gap-3 px-3 mb-8 transition-all ${location.pathname === '/'
                        ? 'bg-gradient-to-br from-anime-primary to-anime-secondary shadow-lg'
                        : 'hover:bg-white/10'
                    }`}
            >
                <span className="text-2xl">🎮</span>
                <span className="font-semibold">Home</span>
            </Link>

            {/* Game Icons */}
            <div className="flex-1 flex flex-col gap-3">
                {games.map((game) => (
                    <Link
                        key={game.id}
                        to={game.path}
                        className={`w-full h-12 rounded-xl flex items-center gap-3 px-3 transition-all ${location.pathname === game.path
                                ? 'bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg'
                                : 'hover:bg-white/10'
                            }`}
                    >
                        <span className="text-2xl">{game.emoji}</span>
                        <span className="font-medium text-sm">{game.name}</span>
                    </Link>
                ))}
            </div>

            {/* Discord User (if available) */}
            {window.discordUser && (
                <div className="w-full h-12 rounded-full bg-discord-blurple flex items-center gap-2 px-3 border-2 border-white/20">
                    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold flex-shrink-0">
                        {window.discordUser.username?.[0]?.toUpperCase() || '?'}
                    </div>
                    <span className="text-xs font-medium truncate">{window.discordUser.username}</span>
                </div>
            )}
        </div>
    )
}
