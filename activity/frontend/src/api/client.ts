import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(
    (config) => {
        const user = window.discordUser
        if (user) config.headers['X-User-ID'] = user.id
        return config
    },
    (error) => Promise.reject(error)
)

api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error.response?.data?.detail || error.message)
        return Promise.reject(error)
    }
)

export const anidleApi = {
    start: (userId: string, difficulty: string) => api.post('/anidle/start', { user_id: userId, difficulty }),
    guess: (gameId: string, animeName: string) => api.post(`/anidle/${gameId}/guess`, { anime_name: animeName }),
    hint: (gameId: string, hintType: string) => api.post(`/anidle/${gameId}/hint`, { hint_type: hintType }),
    giveUp: (gameId: string) => api.post(`/anidle/${gameId}/giveup`),
    status: (gameId: string) => api.get(`/anidle/${gameId}/status`),
    search: (query: string) => api.get('/anidle/search', { params: { q: query, limit: 25 } }),
}

export const guessAnimeApi = {
    start: (userId: string, difficulty: string) => api.post('/guess-anime/start', { user_id: userId, difficulty }),
    guess: (gameId: string, animeName: string) => api.post(`/guess-anime/${gameId}/guess`, { anime_name: animeName }),
    revealStage: (gameId: string) => api.post(`/guess-anime/${gameId}/reveal_stage`),
    navigateStage: (gameId: string, stage: number) => api.post(`/guess-anime/${gameId}/navigate_stage/${stage}`),
    giveUp: (gameId: string) => api.post(`/guess-anime/${gameId}/giveup`),
    status: (gameId: string) => api.get(`/guess-anime/${gameId}/status`),
    search: (query: string) => api.get('/guess-anime/search', { params: { q: query, limit: 25 } }),
}

export const guessCharacterApi = {
    start: (userId: string, difficulty: string) => api.post('/guess-character/start', { user_id: userId, difficulty }),
    guess: (gameId: string, characterName: string, animeName: string) => api.post(`/guess-character/${gameId}/guess`, { character_name: characterName, anime_name: animeName }),
    giveUp: (gameId: string) => api.post(`/guess-character/${gameId}/giveup`),
    status: (gameId: string) => api.get(`/guess-character/${gameId}/status`),
    searchCharacter: (query: string) => api.get('/guess-character/search-character', { params: { q: query, limit: 25 } }),
    searchAnime: (query: string) => api.get('/guess-character/search/anime', { params: { q: query, limit: 25 } }),
}

export const guessOpApi = {
    start: (userId: string, difficulty: string) => api.post('/guess-theme/op/start', { user_id: userId, difficulty }),
    guess: (gameId: string, animeName: string) => api.post(`/guess-theme/${gameId}/guess`, { anime_name: animeName }),
    reveal: (gameId: string) => api.post(`/guess-theme/${gameId}/reveal`),
    giveUp: (gameId: string) => api.post(`/guess-theme/${gameId}/giveup`),
    search: (query: string) => api.get('/guess-theme/search/anime', { params: { q: query, limit: 25 } }),
}

export const guessEdApi = {
    start: (userId: string, difficulty: string) => api.post('/guess-theme/ed/start', { user_id: userId, difficulty }),
    guess: (gameId: string, animeName: string) => api.post(`/guess-theme/${gameId}/guess`, { anime_name: animeName }),
    reveal: (gameId: string) => api.post(`/guess-theme/${gameId}/reveal`),
    giveUp: (gameId: string) => api.post(`/guess-theme/${gameId}/giveup`),
    search: (query: string) => api.get('/guess-theme/search/anime', { params: { q: query, limit: 25 } }),
}

export default api

