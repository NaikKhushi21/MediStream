import { TriageState } from '../types'
import { FileText, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface InterpretationResultsProps {
  state: TriageState
}

export default function InterpretationResults({ state }: InterpretationResultsProps) {
  const biomarkers = Object.values(state.biomarkers)
  const abnormalBiomarkers = biomarkers.filter(b => b.status !== 'normal')

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'normal':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'high':
      case 'low':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'high':
      case 'low':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <div className="flex items-center mb-6">
        <FileText className="w-8 h-8 text-primary-600 mr-3" />
        <h2 className="text-2xl font-semibold">Lab Interpretation Results</h2>
      </div>

      {state.interpretation_summary && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold mb-2 text-blue-900">AI Interpretation Summary</h3>
          <p className="text-blue-800 text-sm">
            {biomarkers.length} biomarker(s) analyzed. {abnormalBiomarkers.length === 0 
              ? 'All values are within normal ranges.' 
              : `${abnormalBiomarkers.length} value(s) require attention.`}
          </p>
        </div>
      )}

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-900">Biomarkers</h3>
          <span className="text-sm text-gray-500">{biomarkers.length} biomarker(s) analyzed</span>
        </div>
        
        {biomarkers.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">No biomarkers extracted.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {biomarkers.map((biomarker, index) => (
              <div
                key={index}
                className={`border-2 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow ${getStatusColor(biomarker.status)}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(biomarker.status)}
                    <h4 className="text-lg font-bold text-gray-900">{biomarker.name}</h4>
                  </div>
                  <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wide ${getStatusColor(biomarker.status)}`}>
                    {biomarker.status}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Measured Value</p>
                    <p className="text-lg font-bold text-gray-900">
                      {biomarker.value.toLocaleString()} {biomarker.unit}
                    </p>
                  </div>
                  {((biomarker.normal_range_min !== null && biomarker.normal_range_min !== undefined) || 
                    (biomarker.normal_range_max !== null && biomarker.normal_range_max !== undefined)) && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Normal Range</p>
                      <p className="text-lg font-semibold text-gray-700">
                        {(biomarker.normal_range_min !== null && biomarker.normal_range_min !== undefined) && 
                         (biomarker.normal_range_max !== null && biomarker.normal_range_max !== undefined)
                          ? `${biomarker.normal_range_min.toLocaleString()} - ${biomarker.normal_range_max.toLocaleString()} ${biomarker.unit}`
                          : (biomarker.normal_range_min !== null && biomarker.normal_range_min !== undefined)
                          ? `≥ ${biomarker.normal_range_min.toLocaleString()} ${biomarker.unit}`
                          : (biomarker.normal_range_max !== null && biomarker.normal_range_max !== undefined)
                          ? `≤ ${biomarker.normal_range_max.toLocaleString()} ${biomarker.unit}`
                          : 'N/A'}
                      </p>
                    </div>
                  )}
                </div>
                
                {biomarker.interpretation && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-700 leading-relaxed">{biomarker.interpretation}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {abnormalBiomarkers.length > 0 && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800">
            <strong>Note:</strong> {abnormalBiomarkers.length} biomarker(s) are outside normal ranges. 
            Please consult with a healthcare provider.
          </p>
        </div>
      )}
    </div>
  )
}
