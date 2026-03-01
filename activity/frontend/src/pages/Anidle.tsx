import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { anidleApi } from '../api/client'
import DifficultySelector from '../components/common/DifficultySelector'
import SearchInput from '../components/common/SearchInput'

interface TagComparison {
    name: string
    status: 'correct' | 'secondary' | 'wrong'
}

interface GenreComparison {
    name: string
    status: 'correct' | 'wrong'
}

interface Comparison {
    title: string
    year: string
    score: string
    episodes: string
    genres: GenreComparison[]
    studio: string
    source: string
    format: string
    media_type: string
    season: string
    tags: TagComparison[]
}

interface GuessAnime {
    title: string
    year: number
    score: number
    image?: string
    media_type?: string
    primary_tags?: string[]
}

interface GameState {
    gameId: string
    guesses: { anime: GuessAnime; comparison: Comparison }[]
    guessesRemaining: number
    isComplete: boolean
    isWon: boolean
    difficulty: string
    target?: {
        title: string
        year: number
        score: number
        episodes: number
        genres: string[]
        studios: string[]
        source: string
        format: string
        media_type: string
        season: string
        primary_tags: string[]
        secondary_tags: string[]
        image: string
    }
    duration?: number
}

const difficultyInfo: Record<string, { emoji: string; label: string; desc: string }> = {
    easy: { emoji: '🟢', label: 'Easy', desc: 'Popular & Well-known Anime' },
    normal: { emoji: '🟡', label: 'Normal', desc: 'Mixed Selection' },
    hard: { emoji: '🟠', label: 'Hard', desc: 'Obscure & Lesser-known' },
    expert: { emoji: '🔴', label: 'Expert', desc: 'Ultra Obscure' },
    crazy: { emoji: '🟣', label: 'Crazy', desc: 'Extremely Challenging' },
    insanity: { emoji: '⚫', label: 'Insanity', desc: 'Impossible Challenge' },
}

export default function Anidle() {
    const [difficulty, setDifficulty] = useState('normal')
    const [isLoading, setIsLoading] = useState(false)
    const [gameState, setGameState] = useState<GameState | null>(null)
    const [searchValue, setSearchValue] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [showHowToPlay, setShowHowToPlay] = useState(false)

    const startGame = async () => {
        setIsLoading(true)
        setError(null)
        try {
            const userId = window.discordUser?.id || 'anonymous'
            const response = await anidleApi.start(userId, difficulty)
            setGameState({
                gameId: response.data.game_id,
                guesses: [],
                guessesRemaining: response.data.max_guesses,
                isComplete: false,
                isWon: false,
                difficulty: difficulty,
            })
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start game')
        } finally {
            setIsLoading(false)
        }
    }

    const makeGuess = async () => {
        if (!gameState || !searchValue.trim()) return
        setIsLoading(true)
        setError(null)
        try {
            const response = await anidleApi.guess(gameState.gameId, searchValue)
            const data = response.data
            setGameState((prev) =>
                prev
                    ? {
                        ...prev,
                        guesses: [...prev.guesses, { anime: data.guess, comparison: data.comparison }],
                        guessesRemaining: data.guesses_remaining,
                        isComplete: data.is_complete,
                        isWon: data.is_won,
                        target: data.target,
                        duration: data.duration,
                    }
                    : null
            )
            setSearchValue('')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit guess')
        } finally {
            setIsLoading(false)
        }
    }

    const giveUp = async () => {
        if (!gameState) return
        setIsLoading(true)
        try {
            const response = await anidleApi.giveUp(gameState.gameId)
            setGameState((prev) =>
                prev
                    ? {
                        ...prev,
                        isComplete: true,
                        isWon: false,
                        target: response.data.target,
                        duration: response.data.duration,
                    }
                    : null
            )
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to give up')
        } finally {
            setIsLoading(false)
        }
    }

    const searchAnime = useCallback(async (query: string) => {
        if (!query || query.length < 2) return []
        try {
            const response = await anidleApi.search(query)
            return response.data.map((item: any) => ({ label: item.name, value: item.value }))
        } catch {
            return []
        }
    }, [])

    // Get status class for simple comparisons
    const getValueStatus = (value: string): 'correct' | 'partial' | 'wrong' => {
        if (value.includes('✅')) return 'correct'
        if (value.includes('⬆️') || value.includes('⬇️')) return 'partial'
        return 'wrong'
    }

    // Get arrow direction if any
    const getArrowDirection = (value: string): 'up' | 'down' | null => {
        if (value.includes('⬆️')) return 'up'
        if (value.includes('⬇️')) return 'down'
        return null
    }

    // Extract clean text without emojis
    const extractText = (value: string) => value.replace(/[✅❌⬆️⬇️]/g, '').trim()

    // Get tag/genre color class - text color only
    const getTagColorClass = (status: string) => {
        switch (status) {
            case 'correct': return 'text-green-400'
            case 'secondary': return 'text-orange-400'
            default: return 'text-red-400'
        }
    }

    // Get cell text color based on status
    const getCellTextClass = (status: 'correct' | 'partial' | 'wrong') => {
        switch (status) {
            case 'correct': return 'text-green-400'
            case 'partial': return 'text-yellow-400'
            default: return 'text-red-400'
        }
    }

    // Start screen
    if (!gameState) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-6">

                <div className="text-center mb-8 animate-fade-in">
                    <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                        🎯 Anidle
                    </h1>
                    <p className="text-xl text-gray-300 mb-2">Guess the anime in 21 tries!</p>
                </div>

                <div className="card p-8 max-w-lg w-full animate-slide-up">
                    <h2 className="text-lg font-semibold mb-4 text-center">Select Difficulty</h2>
                    <DifficultySelector value={difficulty} onChange={setDifficulty} />

                    <div className="mt-6 p-4 bg-white/5 rounded-lg border border-white/10">
                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                            <span>ℹ️</span> How to Play
                        </h3>
                        <div className="text-sm text-gray-300 space-y-2">
                            <p>Guess the anime by comparing properties:</p>
                            <div className="grid grid-cols-2 gap-2 text-xs mt-3">
                                <div className="flex items-center gap-2">
                                    <span className="w-3 h-3 rounded bg-green-500/50"></span> Match
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="w-3 h-3 rounded bg-red-500/50"></span> No match
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-yellow-400">▲</span> Target is higher
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-yellow-400">▼</span> Target is lower
                                </div>
                            </div>
                            <div className="mt-3 pt-3 border-t border-white/10">
                                <p className="mb-2">Tag colors:</p>
                                <div className="flex gap-2 flex-wrap text-xs">
                                    <span className="px-2 py-1 rounded bg-green-500/30 text-green-300">Primary</span>
                                    <span className="px-2 py-1 rounded bg-orange-500/30 text-orange-300">Secondary</span>
                                    <span className="px-2 py-1 rounded bg-red-500/30 text-red-300">Wrong</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {error && (
                        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm text-center">
                            {error}
                        </div>
                    )}

                    <button
                        onClick={startGame}
                        disabled={isLoading}
                        className={`btn btn-primary w-full mt-6 text-lg ${isLoading ? 'btn-disabled' : ''}`}
                    >
                        {isLoading ? 'Starting...' : 'Start Game'}
                    </button>
                </div>
            </div>
        )
    }

    // Result panel component (shown when game is complete)
    const ResultPanel = () => {
        if (!gameState.isComplete || !gameState.target) return null
        const target = gameState.target
        const diff = difficultyInfo[gameState.difficulty] || difficultyInfo.normal

        return (
            <div className="card p-6 mb-6 animate-fade-in">
                <div className="flex items-center gap-4 mb-4">
                    <div className="text-5xl">{gameState.isWon ? '🎉' : '💀'}</div>
                    <div>
                        <h2 className="text-2xl font-bold">
                            {gameState.isWon ? 'Congratulations!' : 'Game Over!'}
                        </h2>
                        <p className="text-gray-400">
                            {gameState.isWon
                                ? `You guessed it in ${gameState.guesses.length} tries!`
                                : 'Better luck next time!'}
                        </p>
                    </div>
                    <div className="ml-auto flex gap-2">
                        <span className="px-3 py-1 bg-white/10 rounded-full text-sm">
                            {diff.emoji} {diff.label}
                        </span>
                        <span className="px-3 py-1 bg-white/10 rounded-full text-sm">
                            {gameState.duration || 0}s
                        </span>
                    </div>
                </div>

                <div className="flex gap-6 bg-white/5 rounded-lg p-4">
                    {target.image && (
                        <img
                            src={target.image}
                            alt={target.title}
                            className="w-32 h-auto rounded-lg shadow-xl flex-shrink-0"
                        />
                    )}
                    <div className="flex-grow">
                        <h3 className="text-xl font-bold text-anime-primary mb-2">{target.title}</h3>
                        <div className="grid grid-cols-3 gap-2 text-sm mb-3">
                            <div><span className="text-gray-400">Year:</span> {target.year || 'N/A'}</div>
                            <div><span className="text-gray-400">Score:</span> {target.score}</div>
                            <div><span className="text-gray-400">Type:</span> {target.media_type || target.format}</div>
                            <div><span className="text-gray-400">Episodes:</span> {target.episodes || 'N/A'}</div>
                            <div><span className="text-gray-400">Source:</span> {target.source}</div>
                            <div><span className="text-gray-400">Season:</span> {target.season}</div>
                        </div>
                        <div className="text-sm mb-2">
                            <span className="text-gray-400">Genres: </span>
                            <span className="text-purple-300">
                                {target.genres?.join(', ') || 'N/A'}
                            </span>
                        </div>
                        <div className="text-sm mb-2">
                            <span className="text-gray-400">Primary Tags: </span>
                            <span className="text-green-400">
                                {target.primary_tags?.join(', ') || 'N/A'}
                            </span>
                        </div>
                        <div className="text-sm">
                            <span className="text-gray-400">Secondary Tags: </span>
                            <span className="text-orange-400">
                                {target.secondary_tags?.join(', ') || 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex gap-4 justify-center mt-4">
                    <button onClick={() => setGameState(null)} className="btn btn-primary">
                        🔄 Play Again
                    </button>
                    <Link to="/" className="btn btn-secondary">
                        🏠 Home
                    </Link>
                </div>
            </div>
        )
    }

    // Active game screen
    const diff = difficultyInfo[gameState.difficulty] || difficultyInfo.normal

    return (
        <div className="min-h-screen p-4 pb-8">
            {/* Header */}
            <div className="text-center pt-10 sm:pt-12 mb-4">
                <h1 className="text-2xl sm:text-3xl font-bold mb-2">🎯 Anidle</h1>
                <div className="flex items-center justify-center gap-3 text-sm flex-wrap">
                    <span className="px-3 py-1 bg-white/10 rounded-full">
                        {diff.emoji} {diff.label}
                    </span>
                    <span className="text-gray-400">
                        Remaining:{' '}
                        <span className={`font-bold ${gameState.guessesRemaining <= 5 ? 'text-red-400' : 'text-white'}`}>
                            {gameState.guessesRemaining}
                        </span>
                    </span>
                </div>
            </div>

            {/* Main content area */}
            <div className="max-w-6xl mx-auto">
                {/* Result panel (when game is complete - above guesses) */}
                <ResultPanel />

                {/* Legend Toggle */}
                <div className="mb-3">
                    <button
                        onClick={() => setShowHowToPlay(!showHowToPlay)}
                        className="text-xs text-gray-400 hover:text-white transition-colors"
                    >
                        {showHowToPlay ? '▼ Hide Legend' : '▶ Show Legend'}
                    </button>
                    {showHowToPlay && (
                        <div className="mt-2 p-3 bg-white/5 rounded-lg text-xs flex gap-6 flex-wrap">
                            <div className="flex gap-3">
                                <span><span className="inline-block w-3 h-3 rounded bg-green-500/50 mr-1"></span> Match</span>
                                <span><span className="inline-block w-3 h-3 rounded bg-red-500/50 mr-1"></span> Wrong</span>
                                <span><span className="text-yellow-400 mr-1">▲</span> Higher</span>
                                <span><span className="text-yellow-400 mr-1">▼</span> Lower</span>
                            </div>
                            <div className="flex gap-2">
                                <span className="px-2 py-0.5 rounded bg-green-500/30 text-green-300">Primary Tag</span>
                                <span className="px-2 py-0.5 rounded bg-orange-500/30 text-orange-300">Secondary Tag</span>
                                <span className="px-2 py-0.5 rounded bg-red-500/30 text-red-300">Wrong Tag</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Guess History - Table Layout */}
                <div className="overflow-x-auto mb-6">
                    {gameState.guesses.length === 0 ? (
                        <div className="text-center text-gray-500 py-8">
                            <p className="text-lg">No guesses yet</p>
                            <p className="text-sm">Start typing an anime name below!</p>
                        </div>
                    ) : (
                        <table className="w-full text-sm border-collapse">
                            <thead>
                                <tr className="text-gray-400 border-b border-white/10">
                                    <th className="text-left py-2 px-2 font-medium">Title</th>
                                    <th className="text-center py-2 px-2 font-medium">Year</th>
                                    <th className="text-center py-2 px-2 font-medium">Format</th>
                                    <th className="text-center py-2 px-2 font-medium">Studio</th>
                                    <th className="text-center py-2 px-2 font-medium">Source</th>
                                    <th className="text-center py-2 px-2 font-medium">Score</th>
                                    <th className="text-center py-2 px-2 font-medium">Genres</th>
                                    <th className="text-left py-2 px-2 font-medium">Tags</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[...gameState.guesses].reverse().map((guess, index) => {
                                    const c = guess.comparison
                                    return (
                                        <tr key={index} className="border-b border-white/5 hover:bg-white/5">
                                            {/* Title */}
                                            <td className="py-2 px-2">
                                                <span className={`font-medium ${getCellTextClass(getValueStatus(c.title))}`}>{extractText(c.title)}</span>
                                            </td>

                                            {/* Year */}
                                            <td className="py-2 px-2 text-center">
                                                <div className={`flex items-center justify-center gap-1 ${getCellTextClass(getValueStatus(c.year))}`}>
                                                    {getArrowDirection(c.year) === 'up' && <span className="text-yellow-400 text-lg">▲</span>}
                                                    {getArrowDirection(c.year) === 'down' && <span className="text-yellow-400 text-lg">▼</span>}
                                                    <span>{extractText(c.year)}</span>
                                                </div>
                                            </td>

                                            {/* Format/Type */}
                                            <td className="py-2 px-2 text-center">
                                                <span className={getCellTextClass(getValueStatus(c.media_type))}>{extractText(c.media_type)}</span>
                                            </td>

                                            {/* Studio */}
                                            <td className="py-2 px-2 text-center">
                                                <span className={getCellTextClass(getValueStatus(c.studio))}>{extractText(c.studio) || '-'}</span>
                                            </td>

                                            {/* Source */}
                                            <td className="py-2 px-2 text-center">
                                                <span className={getCellTextClass(getValueStatus(c.source))}>{extractText(c.source)}</span>
                                            </td>

                                            {/* Score */}
                                            <td className="py-2 px-2 text-center">
                                                <div className={`flex items-center justify-center gap-1 ${getCellTextClass(getValueStatus(c.score))}`}>
                                                    {getArrowDirection(c.score) === 'up' && <span className="text-yellow-400 text-lg">▲</span>}
                                                    {getArrowDirection(c.score) === 'down' && <span className="text-yellow-400 text-lg">▼</span>}
                                                    <span>{extractText(c.score)}</span>
                                                </div>
                                            </td>

                                            {/* Genres */}
                                            <td className="py-2 px-2 align-middle">
                                                <div className="flex flex-col items-center text-xs">
                                                    {(c.genres || []).map((genre, i) => (
                                                        <span key={i} className={getTagColorClass(genre.status)}>{genre.name}</span>
                                                    ))}
                                                    {(!c.genres || c.genres.length === 0) && (
                                                        <span className="text-gray-500">-</span>
                                                    )}
                                                </div>
                                            </td>

                                            {/* Tags */}
                                            <td className="py-2 px-2 align-middle">
                                                <div className="flex flex-col text-xs">
                                                    {(c.tags || []).map((tag, i) => (
                                                        <span key={i} className={getTagColorClass(tag.status)}>{tag.name}</span>
                                                    ))}
                                                    {(!c.tags || c.tags.length === 0) && (
                                                        <span className="text-gray-500">-</span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Input Area */}
                {!gameState.isComplete && (
                    <div className="max-w-2xl mx-auto mb-8">
                        {error && (
                            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm text-center">
                                {error}
                            </div>
                        )}

                        <div className="card p-4">
                            <div className="flex gap-3">
                                <div className="flex-grow">
                                    <SearchInput
                                        value={searchValue}
                                        onChange={setSearchValue}
                                        onSearch={searchAnime}
                                        placeholder="Type anime name..."
                                        onSelect={(value) => setSearchValue(value)}
                                        dropUp={false}
                                    />
                                </div>
                                <button
                                    onClick={makeGuess}
                                    disabled={isLoading || !searchValue.trim()}
                                    className={`btn btn-primary px-6 ${isLoading || !searchValue.trim() ? 'btn-disabled' : ''}`}
                                >
                                    {isLoading ? '...' : 'Guess'}
                                </button>
                                <button onClick={giveUp} disabled={isLoading} className="btn btn-danger px-4">
                                    Give Up
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
