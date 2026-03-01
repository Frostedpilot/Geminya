import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { guessAnimeApi } from '../api/client'
import DifficultySelector from '../components/common/DifficultySelector'
import SearchInput from '../components/common/SearchInput'

interface GameState {
    gameId: string
    currentScreenshot: string
    totalStages: number
    revealedStages: number
    currentStage: number
    nameHintRevealed: boolean
    nameHint?: {
        title?: string
        title_english?: string
        title_japanese?: string
    }
    attemptsRemaining: number
    guesses: string[]
    isComplete: boolean
    isWon: boolean
    difficulty: string
    target?: {
        title: string
        title_english: string
        title_japanese: string
        year: number
        score: number
        episodes: number
        genres: string[]
        studios: string[]
        image: string
    }
    allScreenshots?: string[]
    duration?: number
}

const difficultyInfo = {
    easy: { emoji: '🟢', label: 'Easy' },
    normal: { emoji: '🟡', label: 'Normal' },
    hard: { emoji: '🟠', label: 'Hard' },
    expert: { emoji: '🔴', label: 'Expert' },
    crazy: { emoji: '🟣', label: 'Crazy' },
    insanity: { emoji: '⚫', label: 'Insanity' },
}

export default function GuessAnime() {
    const [difficulty, setDifficulty] = useState('normal')
    const [isLoading, setIsLoading] = useState(false)
    const [gameState, setGameState] = useState<GameState | null>(null)
    const [searchValue, setSearchValue] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [selectedScreenshotIndex, setSelectedScreenshotIndex] = useState(0)

    const startGame = async () => {
        setIsLoading(true)
        setError(null)
        try {
            const userId = window.discordUser?.id || 'anonymous'
            const response = await guessAnimeApi.start(userId, difficulty)
            setGameState({
                gameId: response.data.game_id,
                currentScreenshot: response.data.current_screenshot,
                totalStages: response.data.total_stages,
                revealedStages: response.data.revealed_stages,
                currentStage: response.data.current_stage,
                nameHintRevealed: response.data.name_hint_revealed,
                nameHint: response.data.name_hint,
                attemptsRemaining: response.data.attempts_remaining,
                guesses: [],
                isComplete: false,
                isWon: false,
                difficulty: difficulty,
            })
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start game. Please try again.')
        } finally {
            setIsLoading(false)
        }
    }

    const makeGuess = async () => {
        if (!gameState || !searchValue.trim()) return

        setIsLoading(true)
        setError(null)
        try {
            const response = await guessAnimeApi.guess(gameState.gameId, searchValue)
            const data = response.data

            setGameState((prev) => {
                if (!prev) return null
                return {
                    ...prev,
                    guesses: [...prev.guesses, data.guess],
                    isComplete: data.is_complete,
                    isWon: data.is_won,
                    target: data.target,
                    allScreenshots: data.all_screenshots,
                    duration: data.duration,
                    nameHint: data.name_hint,
                }
            })

            setSearchValue('')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit guess')
        } finally {
            setIsLoading(false)
        }
    }

    const handleStageClick = async (stage: number) => {
        if (!gameState || gameState.isComplete) return

        setIsLoading(true)
        setError(null)
        try {
            let response
            if (stage > gameState.revealedStages) {
                // Reveal next stage
                response = await guessAnimeApi.revealStage(gameState.gameId)
            } else {
                // Navigate to already revealed stage
                response = await guessAnimeApi.navigateStage(gameState.gameId, stage)
            }

            const data = response.data
            setGameState((prev) => {
                if (!prev) return null
                return {
                    ...prev,
                    revealedStages: data.revealed_stages,
                    currentStage: data.current_stage,
                    currentScreenshot: data.current_screenshot || prev.currentScreenshot,
                    nameHintRevealed: data.name_hint_revealed,
                    nameHint: data.name_hint || prev.nameHint,
                }
            })
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to change stage')
        } finally {
            setIsLoading(false)
        }
    }

    const giveUp = async () => {
        if (!gameState) return

        setIsLoading(true)
        try {
            const response = await guessAnimeApi.giveUp(gameState.gameId)
            setGameState((prev) =>
                prev
                    ? {
                        ...prev,
                        isComplete: true,
                        isWon: false,
                        target: response.data.target,
                        allScreenshots: response.data.all_screenshots,
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
            const response = await guessAnimeApi.search(query)
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
                    <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                        📸 Guess Anime
                    </h1>
                    <p className="text-xl text-gray-300 mb-2">Identify the anime from screenshots!</p>
                    <p className="text-gray-400">4 screenshots, 4 attempts. Can you guess it?</p>
                </div>

                <div className="card p-8 max-w-lg w-full animate-slide-up">
                    <h2 className="text-lg font-semibold mb-4 text-center">Select Difficulty</h2>
                    <DifficultySelector value={difficulty} onChange={setDifficulty} />

                    {/* How to Play Section */}
                    <div className="mt-6 p-4 bg-white/5 rounded-lg border border-white/10">
                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                            <span>🎮</span> How to Play
                        </h3>
                        <ul className="text-sm text-gray-300 space-y-2">
                            <li className="flex items-center gap-2">
                                <span className="text-cyan-400">1.</span> Look at the screenshot
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="text-cyan-400">2.</span> Guess which anime it's from
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="text-cyan-400">3.</span> Wrong guess = new screenshot revealed
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="text-cyan-400">4.</span> You have 4 tries total!
                            </li>
                        </ul>
                    </div>

                    {error && (
                        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        onClick={startGame}
                        disabled={isLoading}
                        className={`btn btn-accent w-full mt-6 text-lg ${isLoading ? 'btn-disabled' : ''}`}
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
    if (gameState && gameState.isComplete && gameState.target) {
        const diff = difficultyInfo[gameState.difficulty as keyof typeof difficultyInfo] || difficultyInfo.normal

        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-6">
                <div className="card p-8 max-w-4xl w-full text-center animate-fade-in">
                    <div className="text-7xl mb-4 animate-bounce">{gameState.isWon ? '🎉' : '💀'}</div>
                    <h1 className="text-4xl font-bold mb-2">{gameState.isWon ? 'Correct!' : 'Game Over'}</h1>

                    {/* Difficulty Badge */}
                    <div className="inline-block px-4 py-2 bg-white/10 rounded-full text-sm mb-6">
                        {diff.emoji} {diff.label}
                    </div>

                    {/* Anime Info with Poster */}
                    <div className="flex flex-col md:flex-row gap-6 items-center md:items-start text-left mb-6">
                        {gameState.target.image && (
                            <img
                                src={gameState.target.image}
                                alt={gameState.target.title}
                                className="w-48 h-auto rounded-lg shadow-xl flex-shrink-0"
                            />
                        )}
                        <div className="flex-grow text-center md:text-left">
                            <h2 className="text-2xl font-bold text-anime-accent mb-2">{gameState.target.title}</h2>
                            {gameState.target.title_english && gameState.target.title_english !== gameState.target.title && (
                                <p className="text-gray-400 mb-4">{gameState.target.title_english}</p>
                            )}

                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div>
                                    <span className="text-gray-400">Year:</span> {gameState.target.year || 'N/A'}
                                </div>
                                <div>
                                    <span className="text-gray-400">Score:</span> {gameState.target.score}/10
                                </div>
                                <div>
                                    <span className="text-gray-400">Episodes:</span> {gameState.target.episodes}
                                </div>
                                <div>
                                    <span className="text-gray-400">Genres:</span> {gameState.target.genres?.slice(0, 3).join(', ')}
                                </div>
                                <div className="col-span-2">
                                    <span className="text-gray-400">Studios:</span> {gameState.target.studios?.join(', ') || 'N/A'}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Screenshot Gallery */}
                    {gameState.allScreenshots && gameState.allScreenshots.length > 0 && (
                        <div className="mb-6">
                            <h3 className="text-sm text-gray-400 mb-3">All Screenshots:</h3>
                            <div className="flex justify-center gap-2 overflow-x-auto pb-2">
                                {gameState.allScreenshots.map((ss, index) => (
                                    <button
                                        key={index}
                                        onClick={() => setSelectedScreenshotIndex(index)}
                                        className={`flex-shrink-0 rounded-lg overflow-hidden border-2 transition-all ${selectedScreenshotIndex === index ? 'border-anime-accent scale-105' : 'border-transparent opacity-70 hover:opacity-100'
                                            }`}
                                    >
                                        <img src={ss} alt={`Screenshot ${index + 1}`} className="w-20 h-14 object-cover" />
                                    </button>
                                ))}
                            </div>
                            {/* Large preview of selected screenshot */}
                            <div className="mt-4 rounded-xl overflow-hidden shadow-xl max-w-2xl mx-auto">
                                <img
                                    src={gameState.allScreenshots[selectedScreenshotIndex]}
                                    alt="Selected screenshot"
                                    className="w-full h-auto"
                                />
                            </div>
                        </div>
                    )}

                    {/* Stats */}
                    <div className="flex justify-center gap-8 my-6 p-4 bg-white/5 rounded-lg">
                        <div className="text-center">
                            <div className="text-2xl font-bold">{gameState.revealedStages}/5</div>
                            <div className="text-xs text-gray-400">Hints Used</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold">{gameState.duration}s</div>
                            <div className="text-xs text-gray-400">Time</div>
                        </div>
                    </div>

                    <div className="flex gap-4 justify-center">
                        <button onClick={() => setGameState(null)} className="btn btn-accent">
                            🔄 Play Again
                        </button>
                        <Link to="/" className="btn btn-secondary">
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
                <h1 className="text-3xl font-bold mb-2">📸 Guess Anime</h1>
                <div className="flex items-center justify-center gap-4 text-sm">
                    <span className="px-3 py-1 bg-white/10 rounded-full">
                        {diff.emoji} {diff.label}
                    </span>
                    <span className="text-gray-400">
                        Stage{' '}
                        <span className="text-white font-bold">
                            {gameState.currentStage}/{gameState.totalStages}
                        </span>
                    </span>
                    <span className={`${gameState.attemptsRemaining === 0 ? 'text-red-400' : 'text-yellow-300'} font-semibold`}>
                        ⚠️ Only 1 Guess!
                    </span>
                </div>
            </div>

            {/* Screenshot Display - Always visible */}
            <div className="max-w-3xl mx-auto mb-6">
                    <div className="relative rounded-xl overflow-hidden shadow-2xl bg-black/20">
                        {isLoading && (
                            <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
                                <div className="animate-spin text-4xl">⏳</div>
                            </div>
                        )}
                        <img
                            src={gameState.currentScreenshot}
                            alt="Anime screenshot"
                            className="w-full h-auto animate-fade-in"
                            key={gameState.currentStage}
                        />
                        <div className="absolute bottom-4 right-4 bg-black/70 backdrop-blur-sm px-4 py-2 rounded-full text-white font-medium">
                            📸 Stage {gameState.currentStage}
                        </div>
                    </div>

                    {/* Name Hint Display - Shows alongside current image */}
                    {gameState.nameHintRevealed && gameState.nameHint && (
                        <div className="card p-4 mt-4 bg-yellow-500/10 border-2 border-yellow-500/30">
                            <h3 className="text-sm font-bold mb-3 text-yellow-300 flex items-center gap-2">
                                <span>💡</span> Name Hint
                            </h3>
                            <div className="space-y-2 text-sm">
                                {gameState.nameHint.title_english && (
                                    <div>
                                        <span className="text-gray-400">English:</span>{' '}
                                        <span className="font-mono text-lg text-cyan-400">{gameState.nameHint.title_english}</span>
                                    </div>
                                )}
                                {gameState.nameHint.title && (
                                    <div>
                                        <span className="text-gray-400">Romaji:</span>{' '}
                                        <span className="font-mono text-lg text-cyan-400">{gameState.nameHint.title}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
            </div>

            {/* Stage Navigation Boxes - Wide buttons with labels inside */}
            <div className="max-w-3xl mx-auto mb-6">
                <div className="flex gap-2">
                    {[
                        { stage: 1, label: 'Hint 1' },
                        { stage: 2, label: 'Hint 2' },
                        { stage: 3, label: 'Hint 3' },
                        { stage: 4, label: 'Hint 4' },
                        { stage: 5, label: 'Name' }
                    ].map(({ stage, label }) => {
                        const isRevealed = stage <= gameState.revealedStages
                        const isCurrent = stage === gameState.currentStage
                        const isClickable = isRevealed || stage === gameState.revealedStages + 1
                        const isNameHint = stage === 5
                        const isNameHintRevealed = isNameHint && gameState.nameHintRevealed

                        return (
                            <button
                                key={stage}
                                onClick={() => isClickable && !isNameHintRevealed && handleStageClick(stage)}
                                disabled={!isClickable || isLoading || isNameHintRevealed}
                                className={`flex-1 h-10 rounded-lg font-semibold text-sm flex items-center justify-center gap-1 transition-all transform hover:scale-105 ${
                                    isNameHintRevealed && isNameHint ? 'cursor-not-allowed opacity-50' : ''
                                } ${
                                    isCurrent && !isNameHintRevealed
                                        ? 'bg-gradient-to-br from-cyan-500 to-blue-500 shadow-lg border-2 border-white'
                                        : isRevealed && !isNameHintRevealed
                                        ? 'bg-white/20 hover:bg-white/30 border-2 border-white/30'
                                        : isClickable && !isNameHintRevealed
                                        ? 'bg-white/10 hover:bg-white/20 border-2 border-white/20 animate-pulse'
                                        : 'bg-black/30 border-2 border-white/10 opacity-50 cursor-not-allowed'
                                }`}
                            >
                                <span>{isNameHint ? '💡' : stage}</span>
                                <span>{label}</span>
                            </button>
                        )
                    })}
                </div>
                <p className="text-center text-sm text-gray-400 mt-3">
                    {gameState.revealedStages < 5
                        ? 'Click next box to reveal hint'
                        : 'All hints revealed'}
                </p>
            </div>

            {/* Previous Guess (only 1 allowed) */}
            {gameState.guesses.length > 0 && (
                <div className="max-w-2xl mx-auto mb-6">
                    <div className="card p-4 bg-red-500/20 border-red-500/50">
                        <h3 className="text-sm text-red-300 mb-2 font-semibold">Your Guess:</h3>
                        <span className="text-lg text-red-200 flex items-center gap-2">
                            <span>❌</span> {gameState.guesses[0]}
                        </span>
                    </div>
                </div>
            )}

            {/* Input Area - Part of page content */}
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
                            className={`btn btn-accent px-6 ${isLoading || !searchValue.trim() ? 'btn-disabled' : ''}`}
                        >
                            {isLoading ? '...' : 'Guess'}
                        </button>
                        <button onClick={giveUp} disabled={isLoading} className="btn btn-danger px-4">
                            Give Up
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
