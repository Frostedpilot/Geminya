import { useState, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import { guessCharacterApi } from '../api/client'
import DifficultySelector from '../components/common/DifficultySelector'
import SearchInput from '../components/common/SearchInput'
import { proxyMediaUrl } from '../utils/mediaProxy'

interface CharacterCard {
    gameId: string
    characterImage: string
    characterName: string
    animeName: string
    result?: {
        characterCorrect: boolean
        animeCorrect: boolean
        isWon: boolean
    }
    target?: {
        characterName: string
        animeTitle: string
        animeYear: number
    }
}

interface GameState {
    isComplete: boolean
    isWon: boolean
    difficulty: string
    characters: CharacterCard[]
    duration?: number
}

const difficultyInfo = {
    easy: { emoji: '🟢', label: 'Easy', desc: 'Popular Characters' },
    normal: { emoji: '🟡', label: 'Normal', desc: 'Mixed Selection' },
    hard: { emoji: '🟠', label: 'Hard', desc: 'Obscure Characters' },
    expert: { emoji: '🔴', label: 'Expert', desc: 'Very Obscure' },
    crazy: { emoji: '🟣', label: 'Crazy', desc: 'Extremely Obscure' },
    insanity: { emoji: '⚫', label: 'Insanity', desc: 'Impossible' },
}

export default function GuessCharacter() {
    const [difficulty, setDifficulty] = useState('normal')
    const [isLoading, setIsLoading] = useState(false)
    const [gameState, setGameState] = useState<GameState | null>(null)
    const [error, setError] = useState<string | null>(null)
    const actionInProgress = useRef(false)

    const startGame = async () => {
        setIsLoading(true)
        setError(null)
        try {
            const userId = window.discordUser?.id || 'anonymous'
            const response = await guessCharacterApi.start(userId, difficulty)

            // Initialize characters array from response
            const characters: CharacterCard[] = response.data.characters.map((char: any) => ({
                gameId: char.game_id,
                characterImage: char.character_image,
                characterName: '',
                animeName: '',
            }))

            setGameState({
                isComplete: false,
                isWon: false,
                difficulty: difficulty,
                characters: characters,
            })
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start game. Please try again.')
        } finally {
            setIsLoading(false)
        }
    }

    const updateCharacterInput = (index: number, field: 'characterName' | 'animeName', value: string) => {
        if (!gameState) return
        setGameState(prev => {
            if (!prev) return null
            const newCharacters = [...prev.characters]
            newCharacters[index] = { ...newCharacters[index], [field]: value }
            return { ...prev, characters: newCharacters }
        })
    }

    const makeGuess = async () => {
        if (!gameState || actionInProgress.current) return
        actionInProgress.current = true

        setIsLoading(true)
        setError(null)

        try {
            const updatedCharacters = [...gameState.characters]

            // Only submit guesses for characters that don't have results yet
            const pendingIndices = updatedCharacters
                .map((char, i) => char.result ? -1 : i)
                .filter(i => i !== -1)

            if (pendingIndices.length === 0) return

            const results = await Promise.allSettled(
                pendingIndices.map((i) =>
                    guessCharacterApi.guess(
                        updatedCharacters[i].gameId,
                        updatedCharacters[i].characterName,
                        updatedCharacters[i].animeName
                    )
                )
            )

            let hasError = false

            results.forEach((result, idx) => {
                const i = pendingIndices[idx]
                if (result.status === 'fulfilled') {
                    const data = result.value.data
                    updatedCharacters[i] = {
                        ...updatedCharacters[i],
                        result: {
                            characterCorrect: data.character_correct,
                            animeCorrect: data.anime_correct,
                            isWon: data.is_won,
                        },
                        target: data.target,
                    }
                } else {
                    hasError = true
                }
            })

            if (hasError) {
                setError('Failed to submit some guesses. Please try again.')
                // Still update what succeeded
                setGameState({ ...gameState, characters: updatedCharacters })
                return
            }

            const totalWins = updatedCharacters.filter(c => c.result?.isWon).length

            setGameState({
                ...gameState,
                isComplete: true,
                isWon: totalWins === updatedCharacters.length,
                characters: updatedCharacters,
            })
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit guesses')
        } finally {
            setIsLoading(false)
            actionInProgress.current = false
        }
    }

    const searchCharacter = useCallback(async (query: string) => {
        if (!query || query.length < 2) return []
        try {
            const response = await guessCharacterApi.searchCharacter(query)
            return response.data.map((item: any) => ({
                label: item.name,
                value: item.value,
            }))
        } catch {
            return []
        }
    }, [])

    const searchAnime = useCallback(async (query: string) => {
        if (!query || query.length < 2) return []
        try {
            const response = await guessCharacterApi.searchAnime(query)
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
            <div className="min-h-screen flex flex-col items-center justify-center p-4">
                <div className="text-center mb-6 animate-fade-in">
                    <h1 className="text-3xl lg:text-4xl font-bold mb-3 bg-gradient-to-r from-pink-400 to-purple-400 bg-clip-text text-transparent">
                        🎭 Guess Character
                    </h1>
                    <p className="text-base text-gray-300 mb-1">Name all 4 characters AND their anime!</p>
                    <p className="text-gray-400 text-sm">One chance. Both answers must be correct for each.</p>
                </div>

                <div className="card p-6 max-w-lg w-full animate-slide-up">
                    <h2 className="text-lg font-semibold mb-4 text-center">Select Difficulty</h2>
                    <DifficultySelector value={difficulty} onChange={setDifficulty} />

                    <div className="mt-6 p-4 bg-white/5 rounded-lg border border-white/10">
                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                            <span>⚠️</span> Important
                        </h3>
                        <ul className="text-sm text-gray-300 space-y-2">
                            <li className="flex items-start gap-2">
                                <span className="text-pink-400 flex-shrink-0">•</span>
                                <span>You get <strong className="text-white">ONE chance only!</strong></span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="text-pink-400 flex-shrink-0">•</span>
                                <span>Guess all 4 characters and their anime</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="text-pink-400 flex-shrink-0">•</span>
                                <span>Each character needs both correct answers to count!</span>
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

    // Game complete screen - same layout as game screen but with answers
    if (gameState.isComplete) {
        const diff = difficultyInfo[gameState.difficulty as keyof typeof difficultyInfo] || difficultyInfo.normal
        const correctCount = gameState.characters.filter(c => c.result?.isWon).length

        return (
            <div className="min-h-screen p-3 pb-6">
                {/* Header */}
                <div className="text-center pt-4 mb-4">
                    <div className="text-4xl mb-2">{gameState.isWon ? '🎉' : '💀'}</div>
                    <h1 className="text-2xl font-bold mb-2">
                        {gameState.isWon ? 'Perfect!' : `${correctCount}/4 Correct`}
                    </h1>
                    <div className="flex items-center justify-center gap-4 text-sm">
                        <span className="px-3 py-1 bg-white/10 rounded-full">
                            {diff.emoji} {diff.label}
                        </span>
                    </div>
                </div>

                {/* 4 Card Grid - same as game but with answers */}
                <div className="mx-auto grid grid-cols-4 gap-3 mb-4">
                    {gameState.characters.map((char, index) => (
                        <div key={index} className="card p-2">
                            {/* Character Image */}
                            <div className="relative mb-2">
                                <img
                                    src={proxyMediaUrl(char.characterImage)}
                                    alt={char.target?.characterName || 'Character'}
                                    className="w-full aspect-[3/4] object-cover rounded-lg max-h-48"
                                />
                                {/* Result indicator overlay */}
                                <div className={`absolute top-1 right-1 text-xl ${char.result?.isWon ? '' : ''}`}>
                                    {char.result?.isWon ? '✅' : '❌'}
                                </div>
                            </div>

                            {/* Answer Fields - styled like inputs */}
                            <div className="space-y-2">
                                <div className={`px-2 py-1.5 rounded-lg border text-sm ${char.result?.characterCorrect ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10'}`}>
                                    <span className={char.result?.characterCorrect ? 'text-green-400' : 'text-red-400'}>
                                        {char.target?.characterName}
                                    </span>
                                </div>
                                <div className={`px-2 py-1.5 rounded-lg border text-sm ${char.result?.animeCorrect ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10'}`}>
                                    <span className={char.result?.animeCorrect ? 'text-green-400' : 'text-red-400'}>
                                        {char.target?.animeTitle}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Buttons */}
                <div className="flex gap-4 justify-center">
                    <button
                        onClick={() => setGameState(null)}
                        className="btn btn-secondary"
                    >
                        🔄 Play Again
                    </button>
                    <Link to="/" className="btn btn-primary">
                        🏠 Home
                    </Link>
                </div>
            </div>
        )
    }

    // Active game screen - 4 card layout
    const diff = difficultyInfo[gameState.difficulty as keyof typeof difficultyInfo] || difficultyInfo.normal

    return (
        <div className="min-h-screen p-3 pb-6">
            {/* Header */}
            <div className="text-center pt-4 mb-4">
                <h1 className="text-2xl font-bold mb-2">🎭 Guess Character</h1>
                <div className="flex items-center justify-center gap-4 text-sm">
                    <span className="px-3 py-1 bg-white/10 rounded-full">
                        {diff.emoji} {diff.label}
                    </span>
                </div>
            </div>

            {error && (
                <div className="max-w-6xl mx-auto mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm text-center">
                    {error}
                </div>
            )}

            {/* 4 Card Grid */}
            <div className="mx-auto grid grid-cols-4 gap-3 mb-4">
                {gameState.characters.map((char, index) => (
                    <div key={index} className="card p-2">
                        {/* Character Image */}
                        <div className="relative mb-2">
                            <img
                                src={proxyMediaUrl(char.characterImage)}
                                alt={`Character ${index + 1}`}
                                className="w-full aspect-[3/4] object-cover rounded-lg max-h-48"
                            />
                        </div>

                        {/* Input Fields */}
                        <div className="space-y-2">
                            <div>
                                <SearchInput
                                    value={char.characterName}
                                    onChange={(value) => updateCharacterInput(index, 'characterName', value)}
                                    onSearch={searchCharacter}
                                    placeholder="Character name"
                                    onSelect={(value) => updateCharacterInput(index, 'characterName', value)}
                                    dropUp={false}
                                />
                            </div>
                            <div>
                                <SearchInput
                                    value={char.animeName}
                                    onChange={(value) => updateCharacterInput(index, 'animeName', value)}
                                    onSearch={searchAnime}
                                    placeholder="Anime title"
                                    onSelect={(value) => updateCharacterInput(index, 'animeName', value)}
                                    dropUp={false}
                                />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Submit Button */}
            <div className="max-w-md mx-auto">
                <button
                    onClick={makeGuess}
                    disabled={isLoading}
                    className={`btn btn-secondary w-full py-3 text-base ${isLoading ? 'btn-disabled' : ''}`}
                >
                    {isLoading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="animate-spin">⏳</span> Checking...
                        </span>
                    ) : (
                        'GUESS'
                    )}
                </button>
            </div>
        </div>
    )
}
