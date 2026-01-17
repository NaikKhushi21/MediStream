import PDFPreview from './PDFPreview'

interface RedactedPreviewProps {
  sessionId: string
}

export default function RedactedPreview({ sessionId }: RedactedPreviewProps) {
  return (
    <div>
      <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-start">
          <div className="flex-shrink-0 mr-3">
            <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">✓</span>
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 mb-1">Privacy Protected</p>
            <p className="text-xs text-gray-700 leading-relaxed">
              Personal information has been automatically redacted (shown in yellow) before processing.
            </p>
          </div>
        </div>
      </div>
      
      <PDFPreview 
        sessionId={sessionId}
        title="Redacted Report Preview"
        type="redacted"
      />
      
      <div className="mt-3 px-2">
        <p className="text-xs text-gray-500">Yellow highlights indicate redacted personal information (PII) such as names, dates, and locations.</p>
      </div>
    </div>
  )
}
