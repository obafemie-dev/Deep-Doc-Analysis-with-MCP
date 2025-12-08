import { cn } from '@/lib/utils'

export function TopBar({ mode, onModeChange }) {
  return (
    <div className="h-12 flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-serif font-normal text-gray-900">
          Analyst
        </h1>
        <span className="text-[10px] font-medium text-[#521928] bg-[#5219281A] px-1.5 py-0.5 rounded">
          EARLY PREVIEW
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center bg-gray-100 rounded-full p-0.5 gap-0.5">
          <button
            onClick={() => onModeChange('chat')}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-medium transition-all flex items-center gap-1.5",
              mode === 'chat'
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <span className="material-symbols-rounded text-sm">chat_bubble</span>
            <span>Chat</span>
          </button>
          <button
            onClick={() => onModeChange('sheet')}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-medium transition-all flex items-center gap-1.5",
              mode === 'sheet'
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <span className="material-symbols-rounded text-sm">rubric</span>
            <span>Sheet</span>
          </button>
        </div>
      </div>
    </div>
  )
}

