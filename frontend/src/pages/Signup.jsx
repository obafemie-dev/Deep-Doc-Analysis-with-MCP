import { SignupForm } from '@/components/signup-form'

export default function Signup() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center p-6 md:p-10 bg-white">
      <div className="w-full max-w-sm">
        <SignupForm />
      </div>
    </div>
  )
}

