import { useState, useEffect, useRef, useCallback } from 'react'

interface SearchInputProps {
    value: string
    onChange: (value: string) => void
    onSearch: (query: string) => Promise<{ label: string; value: string }[]>
    onSelect: (value: string) => void
    placeholder?: string
    debounceMs?: number
    dropUp?: boolean // New prop to control dropdown direction
}

export default function SearchInput({
    value,
    onChange,
    onSearch,
    onSelect,
    placeholder = 'Search...',
    debounceMs = 300,
    dropUp = true, // Default to dropping up since inputs are usually at bottom
}: SearchInputProps) {
    const [suggestions, setSuggestions] = useState<{ label: string; value: string }[]>([])
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [highlightIndex, setHighlightIndex] = useState(-1)
    const inputRef = useRef<HTMLInputElement>(null)
    const dropdownRef = useRef<HTMLDivElement>(null)
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    const searchSuggestions = useCallback(async (query: string) => {
        if (!query || query.length < 2) {
            setSuggestions([])
            setIsOpen(false)
            return
        }

        setIsLoading(true)
        try {
            const results = await onSearch(query)
            setSuggestions(results)
            setIsOpen(results.length > 0)
            setHighlightIndex(-1)
        } catch (error) {
            console.error('Search error:', error)
            setSuggestions([])
        } finally {
            setIsLoading(false)
        }
    }, [onSearch])

    useEffect(() => {
        if (debounceRef.current) {
            clearTimeout(debounceRef.current)
        }

        debounceRef.current = setTimeout(() => {
            searchSuggestions(value)
        }, debounceMs)

        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current)
            }
        }
    }, [value, debounceMs, searchSuggestions])

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node) &&
                inputRef.current &&
                !inputRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!isOpen || suggestions.length === 0) {
            if (e.key === 'Enter') {
                e.preventDefault()
            }
            return
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault()
                setHighlightIndex((prev) =>
                    prev < suggestions.length - 1 ? prev + 1 : prev
                )
                break
            case 'ArrowUp':
                e.preventDefault()
                setHighlightIndex((prev) => (prev > 0 ? prev - 1 : -1))
                break
            case 'Enter':
                e.preventDefault()
                if (highlightIndex >= 0 && highlightIndex < suggestions.length) {
                    handleSelect(suggestions[highlightIndex])
                }
                break
            case 'Escape':
                setIsOpen(false)
                break
        }
    }

    const handleSelect = (suggestion: { label: string; value: string }) => {
        onChange(suggestion.value)
        onSelect(suggestion.value)
        setIsOpen(false)
        setSuggestions([])
    }

    // Determine dropdown position classes
    const dropdownPositionClass = dropUp
        ? 'bottom-full mb-1' // Drop up
        : 'top-full mt-1'    // Drop down

    return (
        <div className="relative w-full">
            <div className="relative">
                <input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onFocus={() => suggestions.length > 0 && setIsOpen(true)}
                    placeholder={placeholder}
                    className="input pr-10"
                    autoComplete="off"
                />
                {isLoading && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        <div className="animate-spin w-5 h-5 border-2 border-white/30 border-t-white rounded-full"></div>
                    </div>
                )}
            </div>

            {isOpen && suggestions.length > 0 && (
                <div
                    ref={dropdownRef}
                    className={`absolute z-50 w-full ${dropdownPositionClass} bg-discord-darker border border-white/20 rounded-lg shadow-xl max-h-60 overflow-y-auto`}
                >
                    {suggestions.map((suggestion, index) => (
                        <button
                            key={`${suggestion.value}-${index}`}
                            onClick={() => handleSelect(suggestion)}
                            onMouseEnter={() => setHighlightIndex(index)}
                            className={`w-full px-4 py-2.5 text-left text-sm transition-colors border-b border-white/5 last:border-b-0 ${index === highlightIndex
                                ? 'bg-anime-primary text-white'
                                : 'text-gray-300 hover:bg-white/10'
                                }`}
                        >
                            <span className="line-clamp-1">{suggestion.label}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}
