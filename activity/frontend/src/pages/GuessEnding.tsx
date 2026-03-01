import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { guessEdApi } from '../api/client'
import DifficultySelector from '../components/common/DifficultySelector'
import SearchInput from '../components/common/SearchInput'

interface GameState {
    gameId: string
    themeType: string
    themeSlug: string
    themeUrl: string
    currentStage: number
    maxStage: number
    isComplete: boolean
    isWon: boolean
    difficulty: string
    target?: {
        title: string
        title_english?: string
        year?: number
        image?: string
    }
    theme?: {
        slug: string
        title: string
        artist?: string
    }
    duration?: number
}

const difficultyInfo = {
    easy: { emoji: '🟢', label: 'Easy', desc: 'Popular Anime' },
    normal: { emoji: '🟡', label: 'Normal', desc: 'Mixed Selection' },
    hard: { emoji: '🟠', label: 'Hard', desc: 'Obscure Anime' },
    expert: { emoji: '🔴', label: 'Expert', desc: 'Very Obscure' },
    crazy: { emoji: '🟣', label: 'Crazy', desc: 'Extremely Obscure' },
    insanity: { emoji: '⚫', label: 'Insanity', desc: 'Impossible' },
}

export default function GuessEnding() {
    const [difficulty, setDifficulty] = useState('normal')
    const [isLoading, setIsLoading] = useState(false)
    const [gameState, setGameState] = useState<GameState | null>(null)
    const [animeName, setAnimeName] = useState('')
    const [error, setError] = useState<string | null>(null)

    const startGame = async () => {
        setIsLoading(true)
        setError(null)
        try {
            const userId = window.discordUser?.id || 'anonymous'
            const response = await guessEdApi.start(userId, difficulty)
            setGameState({
                gameId: response.data.game_id,
                themeType: response.data.theme_type,
                themeSlug: response.data.theme_slug,
                themeUrl: response.data.theme_url,
                currentStage: response.data.current_stage,
                maxStage: response.data.max_stage,
                isComplete: false,
                isWon: false,
                difficulty: difficulty,
            })
            setAnimeName('')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start game. Please try again.')
        } finally {
            setIsLoading(false)
        }
    }

    const makeGuess = async () => {
        if (!gameState || !animeName.trim()) return

        setIsLoading(true)
        setError(null)
        try {
            const response = await guessEdApi.guess(gameState.gameId, animeName)
            setGameState(prev => prev ? {
                ...prev,
                isComplete: response.data.is_complete,
                isWon: response.data.is_won,
                target: response.data.target,
                theme: response.data.theme,
                duration: response.data.duration,
            } : null)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit guess')
        } finally {
            setIsLoading(false)
        }
    }

    const revealHint = async () => {
        if (!gameState) return

        setIsLoading(true)
        try {
            const response = await guessEdApi.reveal(gameState.gameId)
            setGameState(prev => prev ? {
                ...prev,
                currentStage: response.data.current_stage,
            } : null)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to reveal hint')
        } finally {
            setIsLoading(false)
        }
    }

    const giveUp = async () => {
        if (!gameState) return

        setIsLoading(true)
        try {
            const response = await guessEdApi.giveUp(gameState.gameId)
            setGameState(prev => prev ? {
                ...prev,
                isComplete: true,
                isWon: false,
                target: response.data.target,
                theme: response.data.theme,
                duration: response.data.duration,
            } : null)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to give up')
        } finally {
            setIsLoading(false)
        }
    }

    const searchAnime = useCallback(async (query: string) => {
        if (!query || query.length < 2) return []
        try {
            const response = await guessEdApi.search(query)
            return response.data.map((item: any) => ({
                label: item.name,
                value: item.value,
            }))
        } catch {
            return []
        }
    }, [])

    // Start screen
    if (!gameState) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-6">
                <div className="text-center mb-8 animate-fade-in">
                    <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                        🎶 Guess the Ending
                    </h1>
                    <p className="text-xl text-gray-300 mb-2">Listen to the ending and guess the anime!</p>
                    <p className="text-gray-400">Stage 1: Audio only → Stage 2: Full video</p>
                </div>

                <div className="card p-8 max-w-lg w-full animate-slide-up">
                    <h2 className="text-lg font-semibold mb-4 text-center">Select Difficulty</h2>
                    <DifficultySelector value={difficulty} onChange={setDifficulty} />

                    {error && (
                        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        onClick={startGame}
                        disabled={isLoading}
                        className={`btn btn-secondary w-full mt-6 text-lg ${isLoading ? 'btn-disabled' : ''}`}
                    >
                        {isLoading ? (
                            <span className="flex items-center justify-center gap-2">
                                <span className="animate-spin">⏳</span> Loading...
                            </span>
                        ) : (
                            'Start Game'
                        )}
                    </button>
                </div>
            </div>
        )
    }

    // Game complete screen
    if (gameState.isComplete && gameState.target) {
        const diff = difficultyInfo[gameState.difficulty as keyof typeof difficultyInfo] || difficultyInfo.normal

        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-6">
                <div className="card p-8 max-w-2xl w-full text-center animate-fade-in">
                    <div className="text-7xl mb-4 animate-bounce">{gameState.isWon ? '🎉' : '💀'}</div>
                    <h1 className="text-4xl font-bold mb-2">{gameState.isWon ? 'Correct!' : 'Wrong!'}</h1>
                    <div className="inline-block px-4 py-2 bg-white/10 rounded-full text-sm mb-6">
                        {diff.emoji} {diff.label}
                    </div>

                    {gameState.target.image && (
                        <img
                            src={gameState.target.image}
                            alt={gameState.target.title}
                            className="w-48 h-auto mx-auto rounded-lg shadow-xl my-4"
                        />
                    )}

                    <h2 className="text-2xl font-bold text-anime-secondary mb-2">{gameState.target.title}</h2>
                    {gameState.target.title_english && gameState.target.title_english !== gameState.target.title && (
                        <p className="text-gray-300 mb-2">{gameState.target.title_english}</p>
                    )}
                    {gameState.target.year && (
                        <p className="text-gray-400 mb-4">({gameState.target.year})</p>
                    )}

                    {gameState.theme && (
                        <div className="p-4 bg-white/5 rounded-lg mb-6">
                            <p className="text-sm text-gray-400">Theme: <span className="text-white">{gameState.theme.slug}</span></p>
                            <p className="text-lg text-anime-secondary">{gameState.theme.title}</p>
                            {gameState.theme.artist && gameState.theme.artist !== 'Unknown' && (
                                <p className="text-sm text-gray-300">by {gameState.theme.artist}</p>
                            )}
                        </div>
                    )}

                    <div className="flex justify-center gap-8 my-4 p-4 bg-white/5 rounded-lg">
                        <div className="text-center">
                            <div className="text-2xl font-bold">{gameState.duration}s</div>
                            <div className="text-xs text-gray-400">Time</div>
                        </div>
                    </div>

                    <div className="flex gap-4 justify-center">
                        <button
                            onClick={() => {
                                setGameState(null)
                                setAnimeName('')
                            }}
                            className="btn btn-secondary"
                        >
                            🔄 Play Again
                        </button>
                        <Link to="/" className="btn btn-primary">
                            🏠 Home
                        </Link>
                    </div>
                </div>
            </div>
        )
    }

    // Active game screen
    const diff = difficultyInfo[gameState.difficulty as keyof typeof difficultyInfo] || difficultyInfo.normal

    return (
        <div className="min-h-screen p-4 pb-8">
            {/* Header */}
            <div className="text-center pt-12 mb-6">
                <h1 className="text-3xl font-bold mb-2">🎶 Guess the Ending</h1>
                <div className="flex items-center justify-center gap-4 text-sm">
                    <span className="px-3 py-1 bg-white/10 rounded-full">
                        {diff.emoji} {diff.label}
                    </span>
                    <span className="px-3 py-1 bg-purple-500/20 rounded-full text-purple-300">
                        {gameState.themeSlug}
                    </span>
                    <span className="px-3 py-1 bg-white/10 rounded-full">
                        Stage {gameState.currentStage}/{gameState.maxStage}
                    </span>
                </div>
            </div>

            {/* Media Player */}
            <div className="max-w-2xl mx-auto mb-6">
                <div className="card p-4">
                    {gameState.currentStage === 1 ? (
                        // Audio only - hide video
                        <div className="relative">
                            <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-lg p-8 text-center mb-4">
                                <div className="text-6xl mb-4">🎶</div>
                                <p className="text-gray-300">Listen to the ending...</p>
                            </div>
                            <audio
                                controls
                                autoPlay
                                className="w-full"
                                src={gameState.themeUrl}
                            >
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                    ) : (
                        // Full video
                        <video
                            controls
                            autoPlay
                            className="w-full rounded-lg"
                            src={gameState.themeUrl}
                        >
                            Your browser does not support the video element.
                        </video>
                    )}
                </div>
            </div>

            {/* Hint button */}
            {gameState.currentStage < gameState.maxStage && (
                <div className="max-w-md mx-auto mb-4 text-center">
                    <button
                        onClick={revealHint}
                        disabled={isLoading}
                        className="btn btn-secondary"
                    >
                        👁️ Show Video (Hint)
                    </button>
                </div>
            )}

            {error && (
                <div className="max-w-md mx-auto mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm text-center">
                    {error}
                </div>
            )}

            {/* Input Area */}
            <div className="max-w-md mx-auto">
                <div className="card p-6">
                    <label className="block text-sm text-gray-400 mb-2">Which anime is this ending from?</label>
                    <SearchInput
                        value={animeName}
                        onChange={setAnimeName}
                        onSearch={searchAnime}
                        placeholder="Enter anime name..."
                        onSelect={(value) => setAnimeName(value)}
                        dropUp={false}
                    />

                    <div className="flex gap-3 mt-4">
                        <button
                            onClick={makeGuess}
                            disabled={isLoading || !animeName.trim()}
                            className={`btn btn-secondary flex-grow py-3 ${isLoading || !animeName.trim() ? 'btn-disabled' : ''}`}
                        >
                            {isLoading ? '⏳ Checking...' : '🎯 Guess'}
                        </button>
                        <button
                            onClick={giveUp}
                            disabled={isLoading}
                            className="btn btn-danger px-6"
                        >
                            Give Up
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
