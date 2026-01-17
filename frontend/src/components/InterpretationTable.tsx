import { TriageState } from '../types'
import { FileText, AlertTriangle, CheckCircle, XCircle, ArrowRight, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface InterpretationTableProps {
  state: TriageState
}

export default function InterpretationTable({ state }: InterpretationTableProps) {
  const biomarkers = Object.values(state.biomarkers)
  const abnormalBiomarkers = biomarkers.filter(b => b.status !== 'normal')
  const criticalBiomarkers = biomarkers.filter(b => b.status === 'critical')
  const highBiomarkers = biomarkers.filter(b => b.status === 'high')
  const lowBiomarkers = biomarkers.filter(b => b.status === 'low')

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'normal':
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'high':
        return <TrendingUp className="w-4 h-4 text-amber-600" />
      case 'low':
        return <TrendingDown className="w-4 h-4 text-amber-600" />
      case 'critical':
        return <XCircle className="w-4 h-4 text-red-600" />
      default:
        return <Minus className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'normal':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 border border-green-200">
            <CheckCircle className="w-3 h-3 mr-1.5" />
            Normal
          </span>
        )
      case 'high':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <TrendingUp className="w-3 h-3 mr-1.5" />
            High
          </span>
        )
      case 'low':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <TrendingDown className="w-3 h-3 mr-1.5" />
            Low
          </span>
        )
      case 'critical':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-red-50 text-red-700 border border-red-200">
            <XCircle className="w-3 h-3 mr-1.5" />
            Critical
          </span>
        )
      default:
        return <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-gray-50 text-gray-700 border border-gray-200">{status}</span>
    }
  }

  const getRowBgColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'bg-red-50/50 hover:bg-red-50'
      case 'high':
      case 'low':
        return 'bg-amber-50/50 hover:bg-amber-50'
      default:
        return 'bg-white hover:bg-gray-50'
    }
  }

  const getRecommendations = () => {
    const recommendations: string[] = []
    
    if (criticalBiomarkers.length > 0) {
      recommendations.push(`⚠️ **${criticalBiomarkers.length} critical value(s) detected.** Please consult with a healthcare provider immediately.`)
    }
    
    if (highBiomarkers.length > 0) {
      recommendations.push(`📈 **${highBiomarkers.length} value(s) above normal range.** Consider discussing with your healthcare provider.`)
    }
    
    if (lowBiomarkers.length > 0) {
      recommendations.push(`📉 **${lowBiomarkers.length} value(s) below normal range.** Consider discussing with your healthcare provider.`)
    }
    
    if (abnormalBiomarkers.length === 0) {
      recommendations.push(`✅ **All biomarker values are within normal ranges.** Continue with your regular health monitoring.`)
    }
    
    criticalBiomarkers.forEach(biomarker => {
      const name = biomarker.name.toLowerCase()
      if (name.includes('vitamin d')) {
        recommendations.push(`💊 **Vitamin D is critically low (${biomarker.value} ${biomarker.unit}).** Your doctor may recommend supplementation and dietary changes.`)
      }
      if (name.includes('glucose') || name.includes('blood sugar')) {
        recommendations.push(`🍎 **Blood sugar levels need attention.** Consult with your doctor about monitoring and potential dietary adjustments.`)
      }
    })
    
    highBiomarkers.forEach(biomarker => {
      const name = biomarker.name.toLowerCase()
      if (name.includes('cholesterol')) {
        recommendations.push(`❤️ **Cholesterol management:** Consider lifestyle changes including a heart-healthy diet, regular exercise, and discussing medication options with your doctor.`)
      }
      if (name.includes('glucose') || name.includes('blood sugar')) {
        recommendations.push(`🍎 **Blood sugar monitoring:** Consider dietary adjustments, regular exercise, and monitoring your glucose levels.`)
      }
    })
    
    lowBiomarkers.forEach(biomarker => {
      const name = biomarker.name.toLowerCase()
      if (name.includes('hemoglobin') || name.includes('iron')) {
        recommendations.push(`🩸 **Low hemoglobin/iron:** Your doctor may recommend iron-rich foods or supplements.`)
      }
    })
    
    return recommendations
  }

  const formatValue = (value: number, unit: string) => {
    if (value % 1 === 0) {
      return `${value.toLocaleString()} ${unit}`
    }
    return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`
  }

  const formatRange = (min: number | null | undefined, max: number | null | undefined, unit: string) => {
    if (min !== null && min !== undefined && max !== null && max !== undefined) {
      return `${min.toLocaleString()} - ${max.toLocaleString()} ${unit}`
    } else if (min !== null && min !== undefined) {
      return `≥ ${min.toLocaleString()} ${unit}`
    } else if (max !== null && max !== undefined) {
      return `≤ ${max.toLocaleString()} ${unit}`
    }
    return 'N/A'
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-200 bg-gray-50/50">
        <div className="flex items-center">
          <div className="bg-blue-600 p-2 rounded-lg mr-3">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Lab Interpretation</h2>
            <p className="text-sm text-gray-600 mt-0.5">{biomarkers.length} biomarker(s) analyzed</p>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      <div className={`mx-6 mt-6 p-4 rounded-lg border ${
        criticalBiomarkers.length > 0 
          ? 'bg-red-50 border-red-200' 
          : abnormalBiomarkers.length > 0 
          ? 'bg-amber-50 border-amber-200' 
          : 'bg-green-50 border-green-200'
      }`}>
        <div className="flex items-center">
          <div className="flex-shrink-0 mr-3">
            {criticalBiomarkers.length > 0 ? (
              <XCircle className="w-5 h-5 text-red-600" />
            ) : abnormalBiomarkers.length > 0 ? (
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            ) : (
              <CheckCircle className="w-5 h-5 text-green-600" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-sm text-gray-900">
              {criticalBiomarkers.length > 0 
                ? 'Critical Values Detected' 
                : abnormalBiomarkers.length > 0 
                ? 'Some Values Need Attention' 
                : 'All Values Normal'}
            </h3>
            <p className="text-sm text-gray-700 mt-0.5">
              {abnormalBiomarkers.length === 0 
                ? 'All biomarker values are within normal ranges.' 
                : `${abnormalBiomarkers.length} value(s) require attention.`}
            </p>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="mx-6 my-6 overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Biomarker
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Your Value
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Normal Range
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Interpretation
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {biomarkers.map((biomarker, index) => (
              <tr 
                key={index} 
                className={`${getRowBgColor(biomarker.status)} transition-colors`}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 mr-2.5">
                      {getStatusIcon(biomarker.status)}
                    </div>
                    <span className="text-sm font-medium text-gray-900">{biomarker.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm font-semibold text-gray-900">
                    {formatValue(biomarker.value, biomarker.unit)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-gray-600">
                    {formatRange(biomarker.normal_range_min, biomarker.normal_range_max, biomarker.unit)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {getStatusBadge(biomarker.status)}
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-gray-700 leading-relaxed">
                    {biomarker.interpretation || 'No interpretation available'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recommendations */}
      <div className="mx-6 mb-6 p-5 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-center mb-4">
          <div className="bg-blue-600 p-2 rounded-lg mr-3">
            <ArrowRight className="w-4 h-4 text-white" />
          </div>
          <h3 className="text-base font-semibold text-gray-900">What You Should Do</h3>
        </div>
        <ul className="space-y-2.5">
          {getRecommendations().map((rec, index) => (
            <li key={index} className="flex items-start text-sm text-gray-800 leading-relaxed">
              <span className="mr-2.5 flex-shrink-0">{rec.split(' ')[0]}</span>
              <span className="flex-1">
                <span dangerouslySetInnerHTML={{ __html: rec.substring(rec.indexOf(' ') + 1).replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>') }} />
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-4 pt-4 border-t border-blue-200">
          <p className="text-xs text-gray-600 leading-relaxed">
            <strong className="font-medium text-gray-900">Important:</strong> This interpretation is for informational purposes only and does not constitute medical advice. 
            Always consult with a qualified healthcare provider for medical decisions.
          </p>
        </div>
      </div>
    </div>
  )
}
