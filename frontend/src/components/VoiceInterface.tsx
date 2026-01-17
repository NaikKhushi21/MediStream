import { useState, useEffect, useRef } from 'react'
import { Mic, MicOff, Volume2 } from 'lucide-react'

interface VoiceInterfaceProps {
  sessionId: string
}

export default function VoiceInterface({ sessionId }: VoiceInterfaceProps) {
  const [isListening, setIsListening] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [transcript, setTranscript] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Initialize WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/ws/voice/${sessionId}`)
    
    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.transcript) {
        setTranscript(data.transcript)
      }
    }
    
    ws.onerror = (error) => {
      setError('WebSocket connection error')
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = () => {
      setIsConnected(false)
    }
    
    wsRef.current = ws
    
    return () => {
      ws.close()
    }
  }, [sessionId])

  const toggleListening = () => {
    if (!isConnected) {
      setError('Not connected to voice service')
      return
    }

    if (isListening) {
      // Stop listening
      setIsListening(false)
      // In production, this would stop the audio stream
    } else {
      // Start listening
      setIsListening(true)
      // In production, this would:
      // 1. Request microphone access
      // 2. Stream audio to OpenAI Realtime API via WebSocket
      // 3. Receive and display transcriptions
      setError('Voice interface requires OpenAI Realtime API integration')
    }
  }

  return (
    <div>
      <div className="flex items-center mb-4">
        <Volume2 className="w-6 h-6 text-primary-600 mr-2" />
        <h2 className="text-xl font-semibold">Voice Interaction</h2>
      </div>
      
      <p className="text-gray-600 mb-4">
        Ask questions about your lab results in real-time using voice.
      </p>

      <div className="flex items-center space-x-4">
        <button
          onClick={toggleListening}
          disabled={!isConnected}
          className={`
            flex items-center px-6 py-3 rounded-lg font-medium transition-colors
            ${isListening
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-primary-600 text-white hover:bg-primary-700'
            }
            ${!isConnected ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          {isListening ? (
            <>
              <MicOff className="w-5 h-5 mr-2" />
              Stop Listening
            </>
          ) : (
            <>
              <Mic className="w-5 h-5 mr-2" />
              Start Voice Chat
            </>
          )}
        </button>

        <div className="flex items-center">
          <div
            className={`w-3 h-3 rounded-full mr-2 ${
              isConnected ? 'bg-green-500' : 'bg-gray-400'
            }`}
          />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {transcript && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Transcript:</p>
          <p className="text-gray-900">{transcript}</p>
        </div>
      )}

      {error && (
        <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">{error}</p>
          <p className="text-xs text-yellow-700 mt-2">
            Note: Full WebRTC integration with OpenAI Realtime API requires additional setup.
            This interface demonstrates the structure for real-time voice interaction.
          </p>
        </div>
      )}

      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Voice Features:</strong> This interface is designed to integrate with OpenAI Realtime API 
          for low-latency voice conversations. The agent's knowledge base includes your current lab 
          interpretation state from LangGraph.
        </p>
      </div>
    </div>
  )
}
