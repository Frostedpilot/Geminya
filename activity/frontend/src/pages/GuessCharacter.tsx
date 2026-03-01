import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { guessCharacterApi } from '../api/client'
import DifficultySelector from '../components/common/DifficultySelector'
import SearchInput from '../components/common/SearchInput'

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
        if (!gameState) return

        setIsLoading(true)
        setError(null)

        try {
            let totalWins = 0
            const updatedCharacters = [...gameState.characters]

            // Submit guess for each character
            for (let i = 0; i < updatedCharacters.length; i++) {
                const char = updatedCharacters[i]
                const response = await guessCharacterApi.guess(char.gameId, char.characterName, char.animeName)
                const data = response.data

                updatedCharacters[i] = {
                    ...char,
                    result: {
                        characterCorrect: data.character_correct,
                        animeCorrect: data.anime_correct,
                        isWon: data.is_won,
                    },
                    target: data.target,
                }

                if (data.is_won) totalWins++
            }

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
            <div className="min-h-screen flex flex-col items-center justify-center p-6">
                <div className="text-center mb-8 animate-fade-in">
                    <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-pink-400 to-purple-400 bg-clip-text text-transparent">
                        🎭 Guess Character
                    </h1>
                    <p className="text-xl text-gray-300 mb-2">Name all 4 characters AND their anime!</p>
                    <p className="text-gray-400">One chance. Both answers must be correct for each.</p>
                </div>

                <div className="card p-8 max-w-lg w-full animate-slide-up">
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
            <div className="min-h-screen p-4 pb-8">
                {/* Header */}
                <div className="text-center pt-12 mb-6">
                    <div className="text-5xl mb-2">{gameState.isWon ? '🎉' : '💀'}</div>
                    <h1 className="text-3xl font-bold mb-2">
                        {gameState.isWon ? 'Perfect!' : `${correctCount}/4 Correct`}
                    </h1>
                    <div className="flex items-center justify-center gap-4 text-sm">
                        <span className="px-3 py-1 bg-white/10 rounded-full">
                            {diff.emoji} {diff.label}
                        </span>
                    </div>
                </div>

                {/* 4 Card Grid - same as game but with answers */}
                <div className="max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {gameState.characters.map((char, index) => (
                        <div key={index} className="card p-4">
                            {/* Character Image */}
                            <div className="relative mb-4">
                                <img
                                    src={char.characterImage}
                                    alt={char.target?.characterName || 'Character'}
                                    className="w-full aspect-[3/4] object-cover rounded-lg"
                                />
                                {/* Result indicator overlay */}
                                <div className={`absolute top-2 right-2 text-2xl ${char.result?.isWon ? '' : ''}`}>
                                    {char.result?.isWon ? '✅' : '❌'}
                                </div>
                            </div>

                            {/* Answer Fields - styled like inputs */}
                            <div className="space-y-3">
                                <div className={`px-3 py-2 rounded-lg border ${char.result?.characterCorrect ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10'}`}>
                                    <span className={char.result?.characterCorrect ? 'text-green-400' : 'text-red-400'}>
                                        {char.target?.characterName}
                                    </span>
                                </div>
                                <div className={`px-3 py-2 rounded-lg border ${char.result?.animeCorrect ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10'}`}>
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
        <div className="min-h-screen p-4 pb-8">
            {/* Header */}
            <div className="text-center pt-12 mb-6">
                <h1 className="text-3xl font-bold mb-2">🎭 Guess Character</h1>
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
            <div className="max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {gameState.characters.map((char, index) => (
                    <div key={index} className="card p-4">
                        {/* Character Image */}
                        <div className="relative mb-4">
                            <img
                                src={char.characterImage}
                                alt={`Character ${index + 1}`}
                                className="w-full aspect-[3/4] object-cover rounded-lg"
                            />
                        </div>

                        {/* Input Fields */}
                        <div className="space-y-3">
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
                    className={`btn btn-secondary w-full py-4 text-lg ${isLoading ? 'btn-disabled' : ''}`}
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
