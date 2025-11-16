import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { GalleryVerticalEnd } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { API_ENDPOINTS } from "@/config/api"

export function SignupForm({
  className,
  ...props
}) {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      // Call backend to send magic link via Stytch
      const response = await fetch(API_ENDPOINTS.SEND_MAGIC_LINK, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to send magic link')
      }

      setSuccess(true)
    } catch (err) {
      console.error('Error sending magic link:', err)
      setError(err.message || 'Failed to send magic link. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className={cn("flex flex-col gap-6", className)} {...props}>
        <div className="flex flex-col items-center gap-4 text-center">
          <img src="/alkanalyst.svg" alt="ALK analyst" className="h-8" />
          <div className="flex flex-col gap-2">
            <h2 className="text-xl font-semibold">Check your email</h2>
            <p className="text-sm text-gray-600">
              We&apos;ve sent a magic link to <strong>{email}</strong>
            </p>
            <p className="text-sm text-gray-600">
              Click the link in the email to create your account and sign in. The link expires in 60 minutes.
            </p>
          </div>
          <Button
            onClick={() => {
              setSuccess(false)
              setEmail("")
            }}
            variant="outline"
            className="w-full mt-4"
          >
            Send another link
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <form onSubmit={handleSubmit}>
        <div className="flex flex-col gap-6">
          <div className="flex flex-col items-center gap-2">
            <img src="/alkanalyst.svg" alt="ALK analyst" className="h-8" />
            <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
              Early Preview
            </span>
            <p className="text-center text-sm text-gray-600 mt-2">
              Create your account with a magic link
            </p>
            <div className="text-center text-sm">
              Already have an account?{" "}
              <a href="/login" className="underline underline-offset-4">
                Login
              </a>
            </div>
          </div>
          <div className="flex flex-col gap-6">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full bg-[#521928] hover:bg-[#3d1320] text-white" disabled={loading}>
              {loading ? 'Sending magic link...' : 'Create account'}
            </Button>
          </div>
        </div>
      </form>
      <div
        className="text-balance text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4 hover:[&_a]:text-primary  ">
        By clicking continue, you agree to our <a href="#">Terms of Service</a>{" "}
        and <a href="#">Privacy Policy</a>.
      </div>
    </div>
  );
}

