interface DifficultySelectorProps {
    value: string
    onChange: (difficulty: string) => void
}

const difficulties = [
    { value: 'easy', label: 'Easy', color: 'bg-green-500', emoji: '🟢' },
    { value: 'normal', label: 'Normal', color: 'bg-yellow-500', emoji: '🟡' },
    { value: 'hard', label: 'Hard', color: 'bg-orange-500', emoji: '🟠' },
    { value: 'expert', label: 'Expert', color: 'bg-red-500', emoji: '🔴' },
    { value: 'crazy', label: 'Crazy', color: 'bg-purple-500', emoji: '🟣' },
    { value: 'insanity', label: 'Insanity', color: 'bg-gray-800', emoji: '⚫' },
]

export default function DifficultySelector({ value, onChange }: DifficultySelectorProps) {
    return (
        <div className="flex flex-wrap justify-center gap-2">
            {difficulties.map((d) => (
                <button
                    key={d.value}
                    onClick={() => onChange(d.value)}
                    className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 transform
            ${value === d.value
                            ? `${d.color} text-white scale-105 shadow-lg`
                            : 'bg-white/10 text-gray-300 hover:bg-white/20 hover:scale-102'
                        }`}
                >
                    {d.emoji} {d.label}
                </button>
            ))}
        </div>
    )
}
