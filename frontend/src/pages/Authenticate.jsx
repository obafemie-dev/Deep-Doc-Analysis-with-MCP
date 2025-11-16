import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { API_ENDPOINTS } from '@/config/api'

export default function Authenticate() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('authenticating') // authenticating, success, error
  const [error, setError] = useState('')

  useEffect(() => {
    const authenticateUser = async () => {
      try {
        // Get token from URL query parameter
        const token = searchParams.get('token')
        const stytch_token_type = searchParams.get('stytch_token_type')

        if (!token) {
          throw new Error('No authentication token found in URL')
        }

        // Call backend to authenticate the magic link token
        const response = await fetch(API_ENDPOINTS.AUTHENTICATE, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
          credentials: 'include', // Important: allows cookies to be set
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || 'Authentication failed')
        }

        // Authentication successful
        setStatus('success')

        // Redirect to main app after a brief delay
        setTimeout(() => {
          navigate('/', { replace: true })
        }, 1500)

      } catch (err) {
        console.error('Authentication error:', err)
        setError(err.message || 'Authentication failed. Please try again.')
        setStatus('error')
      }
    }

    authenticateUser()
  }, [searchParams, navigate])

  if (status === 'authenticating') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white p-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <img src="/alkanalyst.svg" alt="ALK analyst" className="h-8 mx-auto" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#521928] mx-auto"></div>
          <h2 className="text-xl font-semibold">Signing you in...</h2>
          <p className="text-sm text-gray-600">Please wait while we verify your magic link</p>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white p-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <img src="/alkanalyst.svg" alt="ALK analyst" className="h-8 mx-auto" />
          <div className="rounded-full h-12 w-12 bg-green-100 flex items-center justify-center mx-auto">
            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-green-600">Success!</h2>
          <p className="text-sm text-gray-600">You&apos;ve been signed in. Redirecting...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white p-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <img src="/alkanalyst.svg" alt="ALK analyst" className="h-8 mx-auto" />
          <div className="rounded-full h-12 w-12 bg-red-100 flex items-center justify-center mx-auto">
            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-red-600">Authentication Failed</h2>
          <p className="text-sm text-gray-600">{error}</p>
          <Button
            onClick={() => navigate('/login')}
            className="w-full bg-[#521928] hover:bg-[#3d1320] text-white mt-4"
          >
            Back to login
          </Button>
        </div>
        <footer className="absolute bottom-8">
          <img src="/wamiriwordmark.svg" alt="Wamiri" className="h-5 opacity-40" />
        </footer>
      </div>
    )
  }

  return null
}
