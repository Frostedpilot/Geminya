import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { setupDiscord, DiscordUser } from './discord'
import Sidebar from './components/common/Sidebar'
import Home from './pages/Home'
import Anidle from './pages/Anidle'
import GuessAnime from './pages/GuessAnime'
import GuessCharacter from './pages/GuessCharacter'
import GuessOpening from './pages/GuessOpening'
import GuessEnding from './pages/GuessEnding'

declare global {
    interface Window {
        discordUser?: DiscordUser
    }
}

function App() {
    const [isReady, setIsReady] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [_discordUser, setDiscordUser] = useState<DiscordUser | null>(null)

    useEffect(() => {
        async function init() {
            try {
                const isInDiscord = window.location.search.includes('frame_id')

                if (isInDiscord) {
                    const user = await setupDiscord()
                    setDiscordUser(user)
                    window.discordUser = user
                } else {
                    const mockUser: DiscordUser = { id: 'dev_user_123', username: 'Developer', discriminator: '0000', avatar: null }
                    setDiscordUser(mockUser)
                    window.discordUser = mockUser
                }
                setIsReady(true)
            } catch (err) {
                console.error('Failed to initialize Discord SDK:', err)
                setError('Failed to connect to Discord.')
            }
        }
        init()
    }, [])

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="card p-8 text-center">
                    <h1 className="text-2xl font-bold text-red-400 mb-4">Error</h1>
                    <p className="text-gray-300">{error}</p>
                    <button onClick={() => window.location.reload()} className="btn btn-primary mt-6">Retry</button>
                </div>
            </div>
        )
    }

    if (!isReady) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-4 border-anime-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-gray-300">Loading...</p>
                </div>
            </div>
        )
    }

    return (
        <BrowserRouter>
            <div className="min-h-screen flex">
                <Sidebar />
                <div className="flex-1 ml-48">
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/anidle" element={<Anidle />} />
                        <Route path="/guess-anime" element={<GuessAnime />} />
                        <Route path="/guess-character" element={<GuessCharacter />} />
                        <Route path="/guess-opening" element={<GuessOpening />} />
                        <Route path="/guess-ending" element={<GuessEnding />} />
                    </Routes>
                </div>
            </div>
        </BrowserRouter>
    )
}

export default App
