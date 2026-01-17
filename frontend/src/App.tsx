import { useState, useEffect } from 'react'
import { FileText, ArrowLeft } from 'lucide-react'
import LabUpload from './components/LabUpload'
import PDFPreview from './components/PDFPreview'
import RedactedPreview from './components/RedactedPreview'
import InterpretationTable from './components/InterpretationTable'
import Chatbot from './components/Chatbot'
import { TriageState } from './types'
import { api } from './services/api'

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [state, setState] = useState<TriageState | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (sessionId) {
      loadState()
      const interval = setInterval(loadState, 2000) // Poll every 2 seconds
      return () => clearInterval(interval)
    }
  }, [sessionId])

  const loadState = async () => {
    if (!sessionId) return
    try {
      const stateData = await api.getState(sessionId)
      setState(stateData)
    } catch (error) {
      console.error('Error loading state:', error)
    }
  }

  const handleUploadComplete = async (newSessionId: string) => {
    setSessionId(newSessionId)
  }

  const handleInterpret = async () => {
    if (!sessionId) return
    setLoading(true)
    setErrorMessage(null)
    try {
      await api.interpretLab(sessionId)
      await loadState()
    } catch (error: any) {
      console.error('Error interpreting lab:', error)
      const errorMsg = error?.response?.data?.detail || error?.message || 'Unknown error occurred'
      setErrorMessage(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    if (state?.lab_interpreted) {
      // If interpreted, start over
      setSessionId(null)
      setState(null)
      setErrorMessage(null)
    } else if (sessionId) {
      // Go back to upload
      setSessionId(null)
      setState(null)
      setErrorMessage(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-4">
            <div className="bg-blue-600 p-3 rounded-lg">
              <FileText className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            MediStream
          </h1>
          <p className="text-lg text-gray-700 mb-1">
            Agentic Patient Triage & Lab Interpreter
          </p>
          <p className="text-sm text-gray-500">
            HIPAA-conscious • LangGraph • FHIR-compliant
          </p>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {/* Navigation Bar */}
          {(sessionId || state?.lab_interpreted) && (
            <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between">
              <button
                onClick={handleBack}
                className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-md transition-colors"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                {state?.lab_interpreted ? 'Start Over' : 'Back to Upload'}
              </button>
              <div className="flex items-center space-x-2 text-sm">
                <div className={`px-3 py-1.5 rounded-md font-medium ${sessionId ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-500'}`}>
                  Upload
                </div>
                <div className="w-4 h-px bg-gray-300"></div>
                <div className={`px-3 py-1.5 rounded-md font-medium ${state?.lab_interpreted ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-500'}`}>
                  Results
                </div>
              </div>
            </div>
          )}

          {/* Upload Section */}
          {!sessionId && (
            <div className="bg-white rounded-lg border border-gray-200 p-8">
              <LabUpload onUploadComplete={handleUploadComplete} />
            </div>
          )}

          {/* Step 1: Show Preview After Upload */}
          {sessionId && !state?.lab_interpreted && (
            <div className="space-y-6">
              <PDFPreview 
                sessionId={sessionId}
                title="Lab Report Preview"
                type="original"
              />
              
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <button
                  onClick={handleInterpret}
                  disabled={loading}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-base font-medium flex items-center justify-center transition-colors"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                      Interpreting...
                    </>
                  ) : (
                    <>
                      <FileText className="w-5 h-5 mr-2" />
                      Start Interpretation
                    </>
                  )}
                </button>
              </div>

              {errorMessage && (
                <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-4">
                  <p className="text-sm text-red-800 font-medium">{errorMessage}</p>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Show Redacted Preview and Interpretation */}
          {state?.lab_interpreted && (
            <div className="space-y-6">
              <RedactedPreview 
                sessionId={sessionId!}
              />
              
              <InterpretationTable state={state} />
            </div>
          )}

          {/* Step 3: Chatbot */}
          {state?.lab_interpreted && (
            <Chatbot 
              sessionId={sessionId!}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
