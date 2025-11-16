import { LoginForm } from '@/components/login-form'

export default function Login() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <div className="flex flex-1 items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-sm">
          <LoginForm />
        </div>
      </div>
      
      {/* Footer with Wamiri Wordmark */}
      <footer className="flex justify-center pb-8">
        <img src="/wamiriwordmark.svg" alt="Wamiri" className="h-5 opacity-40" />
      </footer>
    </div>
  )
}

