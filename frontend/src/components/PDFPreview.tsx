import { FileText } from 'lucide-react'

interface PDFPreviewProps {
  sessionId: string
  title: string
  type: 'original' | 'redacted'
}

export default function PDFPreview({ sessionId, title, type }: PDFPreviewProps) {
  const pdfUrl = `http://localhost:8000/api/pdf/${sessionId}/${type}#toolbar=0`

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/50">
        <div className="flex items-center">
          <div className="bg-blue-600 p-2 rounded-lg mr-3">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        </div>
      </div>
      
      <div 
        className="bg-gray-50"
        style={{ 
          height: '600px',
          overflow: 'hidden',
          position: 'relative',
          isolation: 'isolate'
        }}
        onWheel={(e) => {
          // Stop scroll propagation to parent
          e.stopPropagation()
        }}
        onTouchMove={(e) => {
          // Stop touch scroll propagation
          e.stopPropagation()
        }}
      >
        <iframe
          src={pdfUrl}
          className="w-full h-full border-0"
          title={title}
          style={{ 
            display: 'block',
            border: 'none',
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'auto'
          }}
        />
      </div>
    </div>
  )
}
