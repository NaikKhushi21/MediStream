import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, AlertCircle } from 'lucide-react'
import { api } from '../services/api'

interface LabUploadProps {
  onUploadComplete: (sessionId: string) => void
}

export default function LabUpload({ onUploadComplete }: LabUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      const result = await api.uploadLab(file)
      onUploadComplete(result.session_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload lab report')
    } finally {
      setUploading(false)
    }
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
    maxFiles: 1,
  })

  return (
    <div>
      <div className="flex items-center mb-4">
        <div className="bg-blue-600 p-2 rounded-lg mr-3">
          <Upload className="w-5 h-5 text-white" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900">Upload Lab Report</h2>
      </div>
      <p className="text-gray-600 mb-6 text-sm leading-relaxed">
        Upload your lab report PDF or image. All PII will be automatically redacted before processing.
      </p>

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} disabled={uploading} />
        
        {uploading ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-700 text-sm font-medium">Uploading and processing...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="bg-blue-50 p-4 rounded-full mb-4">
              <Upload className="w-12 h-12 text-blue-600" />
            </div>
            {isDragActive ? (
              <p className="text-blue-600 font-medium text-base">Drop the file here...</p>
            ) : (
              <>
                <p className="text-gray-900 font-medium mb-2 text-base">
                  Drag & drop your lab report here, or click to select
                </p>
                <p className="text-sm text-gray-500">
                  Supports PDF, PNG, JPG (Max 10MB)
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg flex items-start">
          <AlertCircle className="w-5 h-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800 font-medium">{error}</p>
        </div>
      )}

      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs text-gray-700 leading-relaxed">
          <strong className="font-medium text-gray-900">Privacy Note:</strong> Your lab report is processed locally with Microsoft Presidio 
          to redact PII before any data is sent to AI models. This ensures HIPAA-conscious handling 
          of your sensitive health information.
        </p>
      </div>
    </div>
  )
}
