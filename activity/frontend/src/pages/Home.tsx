import { Link } from 'react-router-dom'

const games = [
    {
        id: 'anidle',
        name: 'Anidle',
        description: 'Guess the anime in 21 tries! Get hints from each guess to narrow it down.',
        emoji: '🎯',
        color: 'from-purple-500 to-pink-500',
        path: '/anidle',
        difficulty: 'Medium',
        tries: '21 tries',
    },
    {
        id: 'guess-anime',
        name: 'Guess Anime',
        description: 'Identify the anime from screenshots. Each wrong guess reveals more!',
        emoji: '📸',
        color: 'from-cyan-500 to-blue-500',
        path: '/guess-anime',
        difficulty: 'Easy',
        tries: '4 tries',
    },
    {
        id: 'guess-character',
        name: 'Guess Character',
        description: 'Name the character AND their anime. High stakes, one chance only!',
        emoji: '🎭',
        color: 'from-pink-500 to-purple-500',
        path: '/guess-character',
        difficulty: 'Hard',
        tries: '1 try',
    },
    {
        id: 'guess-opening',
        name: 'Guess OP',
        description: 'Listen to the opening song and guess which anime it belongs to!',
        emoji: '🎵',
        color: 'from-blue-500 to-cyan-500',
        path: '/guess-opening',
        difficulty: 'Medium',
        tries: '1 try',
    },
    {
        id: 'guess-ending',
        name: 'Guess ED',
        description: 'Listen to the ending song and guess which anime it belongs to!',
        emoji: '🎶',
        color: 'from-purple-500 to-pink-500',
        path: '/guess-ending',
        difficulty: 'Medium',
        tries: '1 try',
    },
]

export default function Home() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-20 left-10 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl"></div>
                <div className="absolute bottom-20 right-10 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl"></div>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-pink-500/5 rounded-full blur-3xl"></div>
            </div>

            {/* Content */}
            <div className="relative z-10 w-full max-w-2xl">
                {/* Header */}
                <div className="text-center mb-8 animate-fade-in">
                    <div className="text-4xl mb-3">🎮</div>
                    <h1 className="text-4xl lg:text-5xl font-bold mb-3 bg-gradient-to-r from-anime-primary via-anime-secondary to-anime-accent bg-clip-text text-transparent">
                        Geminya Games
                    </h1>
                    <p className="text-lg text-gray-300 mb-1">Test your anime knowledge!</p>
                    <p className="text-gray-500 text-sm">Choose a game to get started</p>
                </div>

                {/* Game Selection - Vertical Bars */}
                <div className="flex flex-col gap-3 mb-6">
                    {games.map((game, index) => (
                        <Link
                            key={game.id}
                            to={game.path}
                            className="group animate-slide-up"
                            style={{ animationDelay: `${index * 100}ms` }}
                        >
                            <div className="card card-hover p-4 flex items-center gap-4 relative overflow-hidden">
                                {/* Gradient overlay on hover */}
                                <div
                                    className={`absolute inset-0 bg-gradient-to-r ${game.color} opacity-0 group-hover:opacity-10 transition-opacity duration-300`}
                                ></div>

                                {/* Icon */}
                                <div
                                    className={`w-12 h-12 flex-shrink-0 rounded-lg bg-gradient-to-br ${game.color} flex items-center justify-center text-2xl group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 shadow-lg`}
                                >
                                    {game.emoji}
                                </div>

                                {/* Content */}
                                <div className="flex-grow">
                                    <h2 className="text-xl font-bold mb-1 group-hover:text-anime-primary transition-colors">
                                        {game.name}
                                    </h2>
                                    <p className="text-gray-400 text-xs mb-2">{game.description}</p>
                                    <div className="flex items-center gap-2">
                                        <span className="px-2 py-1 bg-white/10 rounded text-xs text-gray-300">
                                            {game.tries}
                                        </span>
                                        <span
                                            className={`px-2 py-1 rounded text-xs ${game.difficulty === 'Easy'
                                                ? 'bg-green-500/20 text-green-300'
                                                : game.difficulty === 'Medium'
                                                    ? 'bg-yellow-500/20 text-yellow-300'
                                                    : 'bg-red-500/20 text-red-300'
                                                }`}
                                        >
                                            {game.difficulty}
                                        </span>
                                    </div>
                                </div>

                                {/* Arrow */}
                                <div className="flex-shrink-0 text-anime-primary opacity-0 group-hover:opacity-100 transition-all transform group-hover:translate-x-2 text-xl">
                                    →
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>

                {/* Footer */}
                <div className="text-center text-gray-500 text-sm animate-fade-in">
                    <p>Powered by Jikan API & TMDB</p>
                    <p className="mt-1 text-xs text-gray-600">
                        Made with 💜 for anime fans
                    </p>
                </div>
            </div>
        </div>
    )
}
