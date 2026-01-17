import { SpecialistResult } from '../types'
import { Stethoscope, MapPin, Star, ExternalLink } from 'lucide-react'

interface SpecialistResultsProps {
  results: SpecialistResult[]
}

export default function SpecialistResults({ results }: SpecialistResultsProps) {
  if (results.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <div className="flex items-center mb-6">
        <Stethoscope className="w-8 h-8 text-primary-600 mr-3" />
        <h2 className="text-2xl font-semibold">Recommended Specialists</h2>
      </div>

      <div className="grid gap-4">
        {results.map((result, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {result.name}
                </h3>
                
                <div className="flex items-center text-gray-600 mb-2">
                  <Stethoscope className="w-4 h-4 mr-2" />
                  <span>{result.specialty}</span>
                </div>
                
                <div className="flex items-center text-gray-600 mb-2">
                  <MapPin className="w-4 h-4 mr-2" />
                  <span>{result.location}</span>
                  {result.distance && (
                    <span className="ml-2 text-sm text-gray-500">
                      • {result.distance} away
                    </span>
                  )}
                </div>
                
                {result.rating && (
                  <div className="flex items-center text-gray-600">
                    <Star className="w-4 h-4 mr-2 fill-yellow-400 text-yellow-400" />
                    <span>{result.rating}/5.0</span>
                  </div>
                )}
              </div>
              
              {result.url && (
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center"
                >
                  <span className="mr-2">View Profile</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> These results were found using automated browser navigation. 
          Please verify provider credentials and availability before scheduling an appointment.
        </p>
      </div>
    </div>
  )
}
